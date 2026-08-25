import { buildGraph, factor } from "./fx";
import { formatMinor, parseAmount, roundAmount } from "./money";
import { rollup } from "./rollup";

const TOP_LEVEL = ["currencies", "entries", "rates", "reportCurrency"];

interface Document {
  reportCurrency: string;
  currencies: Record<string, number>;
  rates: Array<Record<string, string>>;
  entries: Array<Record<string, string>>;
}

interface Report {
  reportCurrency: string;
  accounts: Array<{ account: string; total: string }>;
}

export function buildReport(value: unknown): Report {
  const document = value as Document;
  const keys = Object.keys(document ?? {})
    .sort()
    .join(",");
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
  const items: Array<[string, bigint]> = [];
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
