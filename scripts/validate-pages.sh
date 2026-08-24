#!/bin/sh
set -eu

test -f docs/index.html
test -f docs/details.html
test -f docs/styles.css
test -f docs/app.js
test -f docs/data/decision-results.json

node --check docs/app.js
node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/decision-results.json", "utf8"));
  if (data.schema_version !== "1.0.0") throw new Error("unexpected aggregate schema");
  if (data.primary.runs !== 22 || data.primary.passed !== 22) throw new Error("unexpected primary totals");
  if (data.all_published.runs !== 24 || data.all_published.passed !== 24) {
    throw new Error("unexpected published totals");
  }
  if (!Array.isArray(data.maturity_summaries) || data.maturity_summaries.length !== 4) {
    throw new Error("expected four JS/TS maturity summaries");
  }
  const examples = new Map(data.polyglot_examples.map((row) => [row.language, row]));
  for (const language of ["python", "go"]) {
    const row = examples.get(language);
    if (!row || row.runs !== 1 || row.passed !== 1 || row.interpretation !== "illustrative_single_run") {
      throw new Error("unexpected illustrative result for " + language);
    }
  }
'

grep -q 'What this benchmark is' docs/index.html
grep -q 'The study found no winner' docs/index.html
grep -q 'What does “6/6 passed” mean?' docs/index.html
grep -q 'Python and Go also completed' docs/index.html
grep -q 'Technical details and operational telemetry' docs/details.html

if grep -R -E 'sk-or-v1-[A-Za-z0-9_-]{20,}' \
  docs/index.html docs/details.html docs/app.js docs/styles.css docs/data; then
  echo "Potential OpenRouter secret found in the public site." >&2
  exit 1
fi

echo "Public report validation passed."
