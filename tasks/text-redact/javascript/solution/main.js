"use strict";

const { codePoints, parseConfig, parseDocument, parseRule } = require("./parse");
const {
  applyMask,
  findSpans,
  hasOverlap,
  keepLongEnough,
  mergeSpans,
} = require("./redact");

function run(value) {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const points = codePoints(document.text);
  const late = process.env.LAB_SABOTAGE === "min-length-after-merge";
  const seen = new Set();
  const stats = [];
  const collected = [];
  for (const item of document.rules) {
    const rule = parseRule(item, seen, points.length);
    seen.add(rule.id);
    let found = findSpans(rule, points);
    if (!late) {
      found = keepLongEnough(found, config.minLength);
    }
    stats.push({ id: rule.id, matches: found.length });
    for (const [start, end] of found) {
      collected.push([start, end, rule.id]);
    }
  }
  if (config.policy === "strict" && hasOverlap(collected)) {
    if (process.env.LAB_SABOTAGE !== "strict-allows-overlap") {
      throw new Error("overlapping spans under the strict policy");
    }
  }
  let spans = mergeSpans(collected);
  if (late) {
    spans = spans.filter((span) => span.end - span.start >= config.minLength);
  }
  const redacted = applyMask(points, spans, config.mask);
  const covered = spans.reduce((total, span) => total + span.end - span.start, 0);
  return {
    redacted,
    spans,
    stats: {
      codePoints: points.length,
      redactedCodePoints: covered,
      rules: stats,
    },
  };
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(JSON.stringify(run(JSON.parse(input))) + "\n");
  } catch (error) {
    process.stderr.write(
      (error instanceof Error ? error.message : String(error)) + "\n",
    );
    process.exit(1);
  }
});
