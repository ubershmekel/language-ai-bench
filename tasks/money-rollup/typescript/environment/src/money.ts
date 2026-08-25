export function parseAmount(text: unknown, minorUnits: number): number {
  return Number(text);
}

export function parseRate(text: unknown): number {
  return Number(text);
}

export function roundAmount(value: number, places: number): bigint {
  const scale = 10 ** places;
  return BigInt(Math.trunc(value * scale + Math.sign(value) * 0.5));
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
