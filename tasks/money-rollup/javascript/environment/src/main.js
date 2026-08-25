"use strict";

const { buildGraph, factor } = require("./fx");
const { formatMinor, parseAmount, roundAmount } = require("./money");
const { rollup } = require("./rollup");

const TOP_LEVEL = ["currencies", "entries", "rates", "reportCurrency"];

function buildReport(document) {
  const keys = Object.keys(document || {}).sort().join(",");
  if (keys !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  const currencies = document.currencies;
  const report = document.reportCurrency;
  if (!(report in currencies)) {
    throw new Error("unknown report currency");
  }
  const edges = buildGraph(currencies, document.rates);
  const places = currencies[report];
  const items = [];
  for (const entry of document.entries) {
    const code = entry.currency;
    const amount = parseAmount(entry.amount, currencies[code]);
    const converted = amount * factor(edges, code, report);
    items.push([entry.account, roundAmount(converted, places)]);
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
