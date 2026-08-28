import type { LiteralRule, Span } from "./parse";

export type Found = [number, number];
export type Attributed = [number, number, string];

/** Scan for the literal one position at a time. */
export function findSpans(rule: LiteralRule, text: string): Found[] {
  const spans: Found[] = [];
  const width = rule.value.length;
  let index = 0;
  while (index + width <= text.length) {
    if (text.slice(index, index + width) === rule.value) {
      spans.push([index, index + width]);
    }
    index += 1;
  }
  return spans;
}

/** Spans are reported in the order they were found. */
export function mergeSpans(spans: Attributed[]): Span[] {
  return spans.map(([start, end, id]) => ({ start, end, rules: [id] }));
}

export function applyMask(text: string, spans: Span[], mask: string): string {
  const characters = text.split("");
  for (const span of spans) {
    for (let index = span.start; index < span.end; index += 1) {
      characters[index] = mask;
    }
  }
  return characters.join("");
}
