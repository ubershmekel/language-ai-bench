import { buildGraph, factor, type Rate } from "./fx";
import { formatMinor, parseAmount, roundAmount } from "./money";
import { rollup, type Item } from "./rollup";

const TOP_LEVEL = ["currencies", "entries", "rates", "reportCurrency"];

export interface Entry {
  account: string;
  currency: string;
  amount: string;
}

export interface Ledger {
  reportCurrency: string;
  currencies: Record<string, number>;
  rates: Rate[];
  entries: Entry[];
}

export interface Report {
  reportCurrency: string;
  accounts: Array<{ account: string; total: string }>;
}

/**
 * Accept the parsed input as a ledger. The current implementation checks only
 * the top-level key set and trusts every value below it.
 */
function asLedger(value: unknown): Ledger {
  const keys = Object.keys(value ?? {})
    .sort()
    .join(",");
  if (keys !== TOP_LEVEL.join(",")) {
    throw new Error("malformed document");
  }
  return value as Ledger;
}

export function buildReport(ledger: Ledger): Report {
  const currencies = ledger.currencies;
  const report = ledger.reportCurrency;
  if (!(report in currencies)) {
    throw new Error("unknown report currency");
  }
  const edges = buildGraph(currencies, ledger.rates);
  const places = currencies[report];
  const items: Item[] = [];
  for (const entry of ledger.entries) {
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
    const report = buildReport(asLedger(JSON.parse(input)));
    process.stdout.write(JSON.stringify(report) + "\n");
  } catch (error) {
    process.stderr.write(
      (error instanceof Error ? error.message : String(error)) + "\n",
    );
    process.exit(1);
  }
});
