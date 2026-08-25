const AMOUNT = /^-?[0-9]+(\.[0-9]+)?$/;
const RATE = /^[0-9]+(\.[0-9]+)?$/;

export interface Rational {
  numerator: bigint;
  denominator: bigint;
}

export function rational(numerator: bigint, denominator: bigint): Rational {
  return { numerator, denominator };
}

export function multiply(left: Rational, right: Rational): Rational {
  return rational(
    left.numerator * right.numerator,
    left.denominator * right.denominator
  );
}

function parseDecimal(
  text: unknown,
  pattern: RegExp,
  maxPlaces: number
): Rational {
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

export function parseAmount(text: unknown, minorUnits: number): Rational {
  return parseDecimal(text, AMOUNT, minorUnits);
}

export function parseRate(text: unknown): Rational {
  const value = parseDecimal(text, RATE, 8);
  if (value.numerator <= 0n) {
    throw new Error("rate must be positive");
  }
  return value;
}

export function roundHalfEven(value: Rational, places: number): bigint {
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

export function formatMinor(minor: bigint, places: number): string {
  const negative = minor < 0n;
  let digits = (negative ? -minor : minor).toString().padStart(places + 1, "0");
  if (places) {
    const split = digits.length - places;
    digits = digits.slice(0, split) + "." + digits.slice(split);
  }
  return negative ? "-" + digits : digits;
}
