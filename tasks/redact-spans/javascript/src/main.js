"use strict";

const { parseConfig, parseDocument, parseRule } = require("./parse");
const { applyMask, findSpans, mergeSpans } = require("./redact");

function run(value) {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const text = document.text;
  const seen = new Set();
  const stats = [];
  const collected = [];
  for (const item of document.rules) {
    const rule = parseRule(item, seen, text.length);
    seen.add(rule.id);
    const found = findSpans(rule, text);
    stats.push({ id: rule.id, matches: found.length });
    for (const [start, end] of found) {
      collected.push([start, end, rule.id]);
    }
  }
  const spans = mergeSpans(collected);
  const redacted = applyMask(text, spans, config.mask);
  const covered = spans.reduce((total, span) => total + span.end - span.start, 0);
  return {
    redacted,
    spans,
    stats: {
      codePoints: text.length,
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
