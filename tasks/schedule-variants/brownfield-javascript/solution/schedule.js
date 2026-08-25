const sabotage = process.env.LAB_SABOTAGE || "";
function canonicalInstant(value) {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toISOString() : null;
}
function exactKeys(value, expected) {
  return (
    value &&
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).sort().join(",") === [...expected].sort().join(",")
  );
}
function normalizeSchedule(value) {
  if (exactKeys(value, ["kind", "at"]) && value.kind === "once") {
    const at = canonicalInstant(value.at);
    return at ? { kind: "once", at } : null;
  }
  if (
    (exactKeys(value, ["kind", "startAt", "everyMinutes"]) ||
      (sabotage === "missing-error-branch" &&
        exactKeys(value, ["kind", "startAt"]))) &&
    value.kind === "interval"
  ) {
    const startAt = canonicalInstant(value.startAt);
    const everyMinutes =
      sabotage === "missing-error-branch" && value.everyMinutes === undefined
        ? 1
        : value.everyMinutes;
    if (!startAt || !Number.isInteger(everyMinutes) || everyMinutes <= 0)
      return null;
    return { kind: "interval", startAt, everyMinutes };
  }
  return null;
}
function nextRun(schedule, afterValue) {
  const after = canonicalInstant(afterValue);
  if (!after) return undefined;
  const afterMs = Date.parse(after);
  if (schedule.kind === "once")
    return Date.parse(schedule.at) > afterMs ? schedule.at : null;
  const startMs = Date.parse(schedule.startAt);
  if (afterMs < startMs) return schedule.startAt;
  const stepMs = schedule.everyMinutes * 60_000;
  const periods =
    Math.floor((afterMs - startMs) / stepMs) +
    (sabotage === "off-by-one" ? 0 : 1);
  return new Date(startMs + periods * stepMs).toISOString();
}
module.exports = { normalizeSchedule, nextRun };
