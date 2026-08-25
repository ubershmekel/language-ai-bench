"use strict";

function parseAmount(text, minorUnits) {
  return Number(text);
}

function parseRate(text) {
  return Number(text);
}

function roundAmount(value, places) {
  const scale = 10 ** places;
  return BigInt(Math.trunc(value * scale + Math.sign(value) * 0.5));
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

module.exports = { formatMinor, parseAmount, parseRate, roundAmount };
