import { evaluate } from "./evaluate";
import { parseDocument, tokenize } from "./parse";

function run(value: Record<string, unknown>): unknown {
  const document = parseDocument(value);
  const results = document.programs.map((program) => ({
    id: program.id,
    value: evaluate(tokenize(program.source)),
  }));
  return { results, stats: { programs: results.length, failed: 0 } };
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk: string) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    process.stdout.write(`${JSON.stringify(run(JSON.parse(input)))}\n`);
  } catch (error) {
    process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
    process.exit(1);
  }
});
