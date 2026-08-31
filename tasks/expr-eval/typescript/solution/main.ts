import { evaluate } from "./evaluate";
import { ProgramError, parseDocument, parseProgram } from "./parse";

interface ValueResult {
  id: string;
  value: bigint;
}

interface ErrorResult {
  id: string;
  code: string;
  at: number;
}

type Result = ValueResult | ErrorResult;

interface Report {
  results: Result[];
  programs: number;
  failed: number;
}

function run(value: unknown): Report {
  const document = parseDocument(value);
  const results: Result[] = [];
  let failed = 0;
  for (const program of document.programs) {
    try {
      const parsed = parseProgram(program.source, document.maxDepth);
      results.push({ id: program.id, value: evaluate(parsed) });
    } catch (error) {
      if (!(error instanceof ProgramError)) {
        throw error;
      }
      failed += 1;
      results.push({ id: program.id, code: error.code, at: error.at });
    }
  }
  return { results, programs: document.programs.length, failed };
}

/** Values are 64 bits wide, so they are written out rather than stringified. */
function render(report: Report): string {
  const items = report.results.map((item) =>
    "value" in item
      ? `{"id":${JSON.stringify(item.id)},"value":${item.value.toString()}}`
      : `{"id":${JSON.stringify(item.id)},"error":{"code":${JSON.stringify(item.code)},"at":${item.at}}}`,
  );
  return (
    `{"results":[${items.join(",")}],` +
    `"stats":{"programs":${report.programs},"failed":${report.failed}}}`
  );
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk: string) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(`${render(run(JSON.parse(input)))}\n`);
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  }
});
