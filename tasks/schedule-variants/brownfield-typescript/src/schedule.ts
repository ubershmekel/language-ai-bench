import type { Schedule } from "./types";

function canonicalInstant(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toISOString() : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

export function normalizeSchedule(value: unknown): Schedule | null {
  if (
    !isRecord(value) ||
    Object.keys(value).sort().join(",") !== "at,kind" ||
    value.kind !== "once"
  ) {
    return null;
  }
  const at = canonicalInstant(value.at);
  return at ? { kind: "once", at } : null;
}

/** Returns the next run, null when there is none, or undefined for a bad `after`. */
export function nextRun(
  schedule: Schedule,
  afterValue: unknown,
): string | null | undefined {
  const after = canonicalInstant(afterValue);
  if (!after) return undefined;
  return Date.parse(schedule.at) > Date.parse(after) ? schedule.at : null;
}
