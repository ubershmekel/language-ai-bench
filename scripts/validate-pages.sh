#!/bin/sh
set -eu

test -f docs/index.html
test -f docs/details.html
test -f docs/styles.css
test -f docs/app.js
test -f docs/data/decision-results.json
test -f docs/data/polyglot-results.json
test -f docs/POLYGLOT_REPORT.md
test -f docs/data/v06-results.json
test -f docs/V06_REPORT.md

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
  if (!Array.isArray(data.language_summaries) || data.language_summaries.length !== 4) {
    throw new Error("expected four language summaries");
  }
  const languages = new Map(data.language_summaries.map((row) => [row.language, row]));
  for (const language of ["javascript", "typescript"]) {
    const row = languages.get(language);
    if (!row || row.runs !== 11 || row.passed !== 11 || row.interpretation !== "balanced_primary") {
      throw new Error("unexpected primary summary for " + language);
    }
  }
  for (const language of ["python", "go"]) {
    const row = languages.get(language);
    if (!row || row.runs !== 1 || row.passed !== 1 || row.interpretation !== "illustrative_single_run") {
      throw new Error("unexpected example summary for " + language);
    }
  }
  const examples = new Map(data.polyglot_examples.map((row) => [row.language, row]));
  for (const language of ["python", "go"]) {
    const row = examples.get(language);
    if (!row || row.runs !== 1 || row.passed !== 1 || row.interpretation !== "illustrative_single_run") {
      throw new Error("unexpected illustrative result for " + language);
    }
  }
'

node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/polyglot-results.json", "utf8"));
  if (data.balanced_polyglot.runs !== 20 || data.balanced_polyglot.passed !== 20) {
    throw new Error("unexpected balanced polyglot totals");
  }
  if (data.all_published.runs !== 32 || data.all_published.passed !== 32) {
    throw new Error("unexpected full-history totals");
  }
  if (data.polyglot_languages.length !== 4 || data.polyglot_languages.some((row) => row.runs !== 5)) {
    throw new Error("expected five balanced runs per language");
  }
  if (data.excluded_infrastructure.length !== 1) throw new Error("expected one infrastructure exclusion");
'
node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/v06-results.json", "utf8"));
  if (data.study_status !== "complete-prospective") throw new Error("unexpected v0.6 status");
  if (data.prospective.runs !== 36 || data.prospective.passed !== 36) throw new Error("unexpected v0.6 totals");
  if (data.languages.length !== 4 || data.languages.some((row) => row.runs !== 9)) throw new Error("expected nine v0.6 runs per language");
  if (data.cells.length !== 12 || data.cells.some((row) => row.runs !== 3)) throw new Error("expected twelve complete v0.6 cells");
  if (data.paired_contrasts.length !== 6 || data.paired_contrasts.some((row) => row.blocks !== 9)) throw new Error("unexpected paired contrasts");
  if (data.task_topology.length !== 12) throw new Error("unexpected topology rows");
  if (data.excluded_infrastructure.length !== 0) throw new Error("unexpected v0.6 infrastructure exclusions");
'

grep -q 'What this benchmark is' docs/index.html
grep -q 'All 36 prospective attempts passed' docs/index.html
grep -q '9 runs · 3 existing tasks' docs/index.html
grep -q 'Older studies remain historical' docs/index.html
grep -q 'Correctness was perfect; historical efficiency telemetry varied' docs/index.html
grep -q 'Same correctness, different path' docs/index.html
grep -q '"workflow_quality"' docs/data/decision-results.json
grep -q 'What does “6/6 passed” mean?' docs/index.html
grep -q 'Python and Go also completed' docs/index.html
grep -q 'Published data at a glance' docs/index.html
grep -q 'Input tokens' docs/index.html
grep -q 'Technical details and paired uncertainty' docs/details.html

if grep -R -E 'sk-or-v1-[A-Za-z0-9_-]{20,}' \
  docs/index.html docs/details.html docs/app.js docs/styles.css docs/data; then
  echo "Potential OpenRouter secret found in the public site." >&2
  exit 1
fi

echo "Public report validation passed."
