function canonicalInstant(value) {
  if (typeof value !== "string") return null;
  const date = new Date(value);
  return Number.isFinite(date.getTime()) ? date.toISOString() : null;
}

function isRecord(value) {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function normalizeSchedule(value) {
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
function nextRun(schedule, afterValue) {
  const after = canonicalInstant(afterValue);
  if (!after) return undefined;
  return Date.parse(schedule.at) > Date.parse(after) ? schedule.at : null;
}

module.exports = { normalizeSchedule, nextRun };
