import { buildGraph, factor } from "./fx";
import { formatMinor, multiply, parseAmount, roundHalfEven } from "./money";
import { rollup } from "./rollup";

const TOP_LEVEL = ["currencies", "entries", "rates", "reportCurrency"];
const ENTRY = ["account", "amount", "currency"];

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join(",") === keys.join(",");
}

interface Report {
  reportCurrency: string;
  accounts: Array<{ account: string; total: string }>;
}

export function buildReport(document: unknown): Report {
  if (!isPlainObject(document) || !hasKeys(document, TOP_LEVEL)) {
    throw new Error("malformed document");
  }
  const currencies = document.currencies;
  if (!isPlainObject(currencies) || !Object.keys(currencies).length) {
    throw new Error("malformed currencies");
  }
  const minorUnits: Record<string, number> = {};
  for (const [code, places] of Object.entries(currencies)) {
    if (typeof places !== "number" || !Number.isInteger(places)) {
      throw new Error("malformed minor units");
    }
    if (places < 0 || places > 4) {
      throw new Error("malformed minor units");
    }
    minorUnits[code] = places;
  }
  const report = document.reportCurrency;
  if (typeof report !== "string" || !(report in minorUnits)) {
    throw new Error("unknown report currency");
  }
  if (!Array.isArray(document.rates) || !Array.isArray(document.entries)) {
    throw new Error("malformed sections");
  }
  const edges = buildGraph(minorUnits, document.rates);
  const places = minorUnits[report];
  const items: Array<[unknown, bigint]> = [];
  for (const value of document.entries) {
    if (!isPlainObject(value) || !hasKeys(value, ENTRY)) {
      throw new Error("malformed entry");
    }
    const code = value.currency;
    if (typeof code !== "string" || !(code in minorUnits)) {
      throw new Error("unknown entry currency");
    }
    const amount = parseAmount(value.amount, minorUnits[code]);
    const converted = multiply(amount, factor(edges, code, report));
    items.push([value.account, roundHalfEven(converted, places)]);
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
process.stdin.on("data", (chunk: string) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(JSON.stringify(buildReport(JSON.parse(input))) + "\n");
  } catch (error) {
    process.stderr.write(String((error as Error).message) + "\n");
    process.exit(1);
  }
});
