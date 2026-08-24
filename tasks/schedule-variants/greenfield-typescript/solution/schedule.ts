import { Schedule } from "./types";
const sabotage = process.env.LAB_SABOTAGE ?? "";
function canonicalInstant(value: unknown): string | null { if (typeof value !== "string") return null; const date = new Date(value); return Number.isFinite(date.getTime()) ? date.toISOString() : null; }
function record(value: unknown): value is Record<string, unknown> { return !!value && typeof value === "object" && !Array.isArray(value); }
function exactKeys(value: Record<string, unknown>, expected: string[]): boolean { return Object.keys(value).sort().join(",") === [...expected].sort().join(","); }
export function normalizeSchedule(value: unknown): Schedule | null {
  if (!record(value)) return null;
  if (exactKeys(value, ["kind", "at"]) && value.kind === "once") { const at = canonicalInstant(value.at); return at ? { kind: "once", at } : null; }
  if ((exactKeys(value, ["kind", "startAt", "everyMinutes"]) || (sabotage === "missing-error-branch" && exactKeys(value, ["kind", "startAt"]))) && value.kind === "interval") { const startAt = canonicalInstant(value.startAt); const everyMinutes = sabotage === "missing-error-branch" && value.everyMinutes === undefined ? 1 : value.everyMinutes; if (!startAt || !Number.isInteger(everyMinutes) || (everyMinutes as number) <= 0) return null; return { kind: "interval", startAt, everyMinutes: everyMinutes as number }; }
  return null;
}
export function nextRun(schedule: Schedule, afterValue: unknown): string | null | undefined {
  const after = canonicalInstant(afterValue); if (!after) return undefined; const afterMs = Date.parse(after);
  if (schedule.kind === "once") return Date.parse(schedule.at) > afterMs ? schedule.at : null;
  const startMs = Date.parse(schedule.startAt); if (afterMs < startMs) return schedule.startAt; const stepMs = schedule.everyMinutes * 60_000;
  const periods = Math.floor((afterMs - startMs) / stepMs) + (sabotage === "off-by-one" ? 0 : 1); return new Date(startMs + periods * stepMs).toISOString();
}
