"use strict";

/** Scan for the literal one position at a time. */
function findSpans(rule, text) {
  const spans = [];
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
function mergeSpans(spans) {
  return spans.map(([start, end, id]) => ({ start, end, rules: [id] }));
}

function applyMask(text, spans, mask) {
  const characters = text.split("");
  for (const span of spans) {
    for (let index = span.start; index < span.end; index += 1) {
      characters[index] = mask;
    }
  }
  return characters.join("");
}

module.exports = { applyMask, findSpans, mergeSpans };
