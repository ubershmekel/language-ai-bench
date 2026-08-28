import { parseConfig, parseDocument, parseRule } from "./parse";
import type { Span } from "./parse";
import { applyMask, findSpans, mergeSpans } from "./redact";
import type { Attributed } from "./redact";

interface RuleStat {
  id: string;
  matches: number;
}

interface Result {
  redacted: string;
  spans: Span[];
  stats: {
    codePoints: number;
    redactedCodePoints: number;
    rules: RuleStat[];
  };
}

export function run(value: unknown): Result {
  const document = parseDocument(value);
  const config = parseConfig(document.config);
  const text = document.text;
  const seen = new Set<string>();
  const stats: RuleStat[] = [];
  const collected: Attributed[] = [];
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
process.stdin.on("data", (chunk: string) => {
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
