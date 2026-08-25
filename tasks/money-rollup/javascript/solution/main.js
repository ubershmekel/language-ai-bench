"use strict";

const { buildGraph, factor } = require("./fx");
const {
  formatMinor,
  multiply,
  parseAmount,
  roundHalfEven,
} = require("./money");
const { rollup } = require("./rollup");

const TOP_LEVEL = ["currencies", "entries", "rates", "reportCurrency"];
const ENTRY = ["account", "amount", "currency"];

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value, keys) {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

function buildReport(document) {
  if (!isPlainObject(document) || !hasKeys(document, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  const currencies = document.currencies;
  if (!isPlainObject(currencies) || !Object.keys(currencies).length) {
    throw new Error("malformed currencies");
  }
  for (const minorUnits of Object.values(currencies)) {
    if (typeof minorUnits !== "number" || !Number.isInteger(minorUnits)) {
      throw new Error("malformed minor units");
    }
    if (minorUnits < 0 || minorUnits > 4) {
      throw new Error("malformed minor units");
    }
  }
  const report = document.reportCurrency;
  if (typeof report !== "string" || !(report in currencies)) {
    throw new Error("unknown report currency");
  }
  if (!Array.isArray(document.rates) || !Array.isArray(document.entries)) {
    throw new Error("malformed sections");
  }
  const edges = buildGraph(currencies, document.rates);
  const places = currencies[report];
  const items = [];
  for (const entry of document.entries) {
    if (!isPlainObject(entry) || !hasKeys(entry, ENTRY)) {
      throw new Error("malformed entry");
    }
    const code = entry.currency;
    if (typeof code !== "string" || !(code in currencies)) {
      throw new Error("unknown entry currency");
    }
    const amount = parseAmount(entry.amount, currencies[code]);
    const converted = multiply(amount, factor(edges, code, report));
    items.push([entry.account, roundHalfEven(converted, places)]);
  }
  return {
    reportCurrency: report,
    accounts: rollup(items).map(([account, total]) => ({
      account,
      total: formatMinor(total, places),
    })),
  };
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(JSON.stringify(buildReport(JSON.parse(input))) + "\n");
  } catch (error) {
    process.stderr.write(String(error.message) + "\n");
    process.exit(1);
  }
});
