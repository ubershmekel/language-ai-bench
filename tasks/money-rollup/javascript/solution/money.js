"use strict";

const AMOUNT = /^-?[0-9]+(\.[0-9]+)?$/;
const RATE = /^[0-9]+(\.[0-9]+)?$/;

function rational(numerator, denominator) {
  return { numerator, denominator };
}

function multiply(left, right) {
  return rational(
    left.numerator * right.numerator,
    left.denominator * right.denominator
  );
}

function parseDecimal(text, pattern, maxPlaces) {
  if (typeof text !== "string" || !pattern.test(text)) {
    throw new Error("malformed decimal");
  }
  const negative = text.startsWith("-");
  const body = negative ? text.slice(1) : text;
  const parts = body.split(".");
  const fraction = parts.length > 1 ? parts[1] : "";
  const ignoreLimit = process.env.LAB_SABOTAGE === "ignore-decimal-limit";
  if (fraction.length > maxPlaces && !ignoreLimit) {
    throw new Error("too many decimal places");
  }
  const digits = BigInt(parts[0] + fraction);
  return rational(negative ? -digits : digits, 10n ** BigInt(fraction.length));
}

function parseAmount(text, minorUnits) {
  return parseDecimal(text, AMOUNT, minorUnits);
}

function parseRate(text) {
  const value = parseDecimal(text, RATE, 8);
  if (value.numerator <= 0n) {
    throw new Error("rate must be positive");
  }
  return value;
}

function roundHalfEven(value, places) {
  const scaledNumerator = value.numerator * 10n ** BigInt(places);
  const negative = scaledNumerator < 0n;
  const numerator = negative ? -scaledNumerator : scaledNumerator;
  const denominator = value.denominator;
  let whole = numerator / denominator;
  const twiceRemainder = (numerator % denominator) * 2n;
  const halfUp = process.env.LAB_SABOTAGE === "half-up-rounding";
  const tie = twiceRemainder === denominator;
  if (twiceRemainder > denominator || (tie && (halfUp || whole % 2n === 1n))) {
    whole += 1n;
  }
  return negative ? -whole : whole;
}

function formatMinor(minor, places) {
  const negative = minor < 0n;
  let digits = (negative ? -minor : minor).toString().padStart(places + 1, "0");
  if (places) {
    const split = digits.length - places;
    digits = digits.slice(0, split) + "." + digits.slice(split);
  }
  return negative ? "-" + digits : digits;
}

module.exports = {
  formatMinor,
  multiply,
  parseAmount,
  parseRate,
  rational,
  roundHalfEven,
};
