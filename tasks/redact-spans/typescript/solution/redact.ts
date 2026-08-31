import { codePoints } from "./parse";
import type { Rule, Span } from "./parse";

export type Found = [number, number];
export type Attributed = [number, number, string];

const sabotage = process.env["LAB_SABOTAGE"] ?? "";

/** Every non-overlapping occurrence, scanning left to right. */
export function findSpans(rule: Rule, points: string[]): Found[] {
  if (rule.kind === "span") {
    return [[rule.start, rule.end]];
  }
  const value = codePoints(rule.value);
  const width = value.length;
  const spans: Found[] = [];
  let index = 0;
  while (index + width <= points.length) {
    let same = true;
    for (let offset = 0; offset < width; offset += 1) {
      if (points[index + offset] !== value[offset]) {
        same = false;
        break;
      }
    }
    if (same) {
      spans.push([index, index + width]);
      index += sabotage === "overlapping-literal-matches" ? 1 : width;
    } else {
      index += 1;
    }
  }
  return spans;
}

export function keepLongEnough(spans: Found[], minimum: number): Found[] {
  return spans.filter(([start, end]) => end - start >= minimum);
}

export function hasOverlap(spans: Attributed[]): boolean {
  const ordered = [...spans].sort(
    (left, right) => left[0] - right[0] || left[1] - right[1],
  );
  for (let index = 1; index < ordered.length; index += 1) {
    if (ordered[index]![0] < ordered[index - 1]![1]) {
      return true;
    }
  }
  return false;
}

interface Growing {
  start: number;
  end: number;
  rules: Set<string>;
}

/** Combine spans that overlap or touch, keeping every contributing id. */
export function mergeSpans(spans: Attributed[]): Span[] {
  const joined = sabotage !== "merge-drops-touching";
  const ordered = [...spans].sort(
    (left, right) =>
      left[0] - right[0] ||
      left[1] - right[1] ||
      (left[2] < right[2] ? -1 : left[2] > right[2] ? 1 : 0),
  );
  const merged: Growing[] = [];
  for (const [start, end, id] of ordered) {
    const last = merged[merged.length - 1];
    if (last && (start < last.end || (joined && start === last.end))) {
      last.end = Math.max(last.end, end);
      last.rules.add(id);
    } else {
      merged.push({ start, end, rules: new Set([id]) });
    }
  }
  return merged.map((item) => ({
    start: item.start,
    end: item.end,
    rules: [...item.rules].sort((left, right) =>
      left < right ? -1 : left > right ? 1 : 0,
    ),
  }));
}

export function applyMask(
  points: string[],
  spans: Span[],
  mask: string,
): string {
  const masked = [...points];
  for (const span of spans) {
    for (let index = span.start; index < span.end; index += 1) {
      masked[index] = mask;
    }
  }
  return masked.join("");
}
