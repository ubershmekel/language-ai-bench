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
test -f docs/data/v07-results.json
test -f docs/V07_REPORT.md
test -f docs/data/v08-results.json
test -f docs/V08_REPORT.md
test -f docs/data/v09-results.json
test -f docs/data/v10-results.json
test -f docs/V09_REPORT.md

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

grep -q 'id="glance-title">Results<' docs/index.html
test -f docs/methodology.html
grep -q 'methodology.html' docs/index.html

# Reader-facing copy should not lean on internal jargon.
if grep -Ewq 'arms?' docs/index.html; then
  echo "Internal jargon (arm/arms) found in landing page copy." >&2
  exit 1
fi
# The effort contrast must still be stated in words, either direction.
grep -q 'agent steps than' docs/index.html

node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/v07-results.json", "utf8"));
  if (data.study_status !== "complete-prospective") throw new Error("unexpected v0.7 status");
  const strong = data.rungs.find((rung) => rung.rung === "strong");
  if (!strong) throw new Error("missing strong rung");
  if (strong.runs % 48 !== 0) throw new Error("expected whole strong-rung batches of 48");
  if (strong.languages.some((row) => row.runs !== strong.runs / 4)) {
    throw new Error("strong rung is unbalanced across languages");
  }
  if (strong.passed === strong.runs) throw new Error("strong rung saturated again; the family no longer discriminates");
  if (strong.languages.length !== 4) throw new Error("expected four v0.7 languages");
  if (strong.paired_contrasts.length !== 6) throw new Error("unexpected v0.7 paired contrasts");
'
node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/v08-results.json", "utf8"));
  if (data.schema_version !== "1.0.0") throw new Error("unexpected v0.8 schema");
  if (data.rollouts !== 120) throw new Error("expected 120 v0.8 rollouts");
  if (data.by_arm.length !== 5) throw new Error("expected five v0.8 arms");
  if (data.by_arm.some((row) => row.runs !== data.rollouts / 5)) {
    throw new Error("v0.8 cohort is unbalanced across arms");
  }
  if (data.by_arm.some((row) => "mean_agent_seconds" in row)) {
    throw new Error("v0.8 ran concurrently; elapsed time must not be published");
  }
  const primary = data.primary_contrast;
  if (!primary || primary.left !== "python-typed" || primary.right !== "python") {
    throw new Error("primary contrast must be oriented typed minus untyped");
  }
  // Guards the sign bug: the paired bootstrap stores python minus python-typed.
  const unpaired = new Map(data.by_arm.map((row) => [row.language, row.pass_rate]));
  const expected = unpaired.get("python-typed") - unpaired.get("python");
  const reported = primary.estimates.hidden_test_pass.mean_difference;
  if (Math.sign(expected) !== Math.sign(reported)) {
    throw new Error("primary contrast sign disagrees with the arm totals");
  }
  const families = new Set(data.by_family_and_arm.map((row) => row.task_family));
  if (families.size !== 3) throw new Error("expected three v0.8 families");
'
grep -q 'family-reversal' docs/index.html
node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/v09-results.json", "utf8"));
  if (data.schema_version !== "1.0.0") throw new Error("unexpected v0.9 schema");
  if (data.rollouts !== 120) throw new Error("expected 120 v0.9 rollouts");
  if (data.by_arm.length !== 5) throw new Error("expected five v0.9 arms");
  if (data.by_arm.some((row) => row.runs !== data.rollouts / 5)) {
    throw new Error("v0.9 cohort is unbalanced across arms");
  }
  if (data.by_arm.some((row) => "mean_agent_seconds" in row)) {
    throw new Error("v0.9 ran concurrently; elapsed time must not be published");
  }
  const families = new Set(data.by_family_and_arm.map((row) => row.task_family));
  if (families.size !== 3) throw new Error("expected three v0.9 families");
  if (!families.has("text-redact")) throw new Error("v0.9 must carry the third family");
  // The third family saturated. Publishing it as an ordering would be a lie,
  // so the site drops any family with under two runs of separation and the
  // report has to keep saying that out loud.
  const spread = data.leadership.spread_runs;
  if (spread["text-redact"] >= 2) {
    throw new Error("text-redact now discriminates; revisit the copy calling it too easy");
  }
  if (data.leadership.flat_families.join() !== "text-redact") {
    throw new Error("unexpected set of flat v0.9 families");
  }
  const cp = data.text_redact_code_point_failures;
  if (cp.length !== 5) throw new Error("expected five code point rows");
'

# The published cohort is v1.0. The site loads it at runtime, so the JSON and the
# static fallbacks in the markup have to agree about which tasks rank anything.
node -e '
  const fs = require("node:fs");
  const data = JSON.parse(fs.readFileSync("docs/data/v10-results.json", "utf8"));
  const html = fs.readFileSync("docs/index.html", "utf8");
  if (data.schema_version !== "1.0.0") throw new Error("unexpected v1.0 schema");
  if (data.by_arm.length !== 5) throw new Error("expected five v1.0 arms");
  if (data.by_arm.some((row) => "mean_agent_seconds" in row)) {
    throw new Error("v1.0 ran concurrently; elapsed time must not be published");
  }
  const families = new Set(data.by_family_and_arm.map((row) => row.task_family));
  if (families.size !== 3) throw new Error("expected three v1.0 families");
  if (!families.has("expr-eval")) throw new Error("v1.0 must carry expr-eval");
  if (!html.includes("./data/v10-results.json") && !fs.readFileSync("docs/app.js", "utf8").includes("v10-results.json")) {
    throw new Error("the site does not load the published cohort");
  }
  // Every task is listed, and setups within a run of each other are joined by
  // an approximation sign rather than a greater-than: eight attempts cannot
  // separate them, so a ">" there would read as a ranking that is not there.
  const listed = [...html.matchAll(/<li><code>([a-z-]+)<\/code>([^<]*)</g)];
  if (listed.length !== families.size) {
    throw new Error(`site lists ${listed.length} tasks but the cohort has ${families.size}`);
  }
  for (const [, family, rendered] of listed) {
    if (!families.has(family)) throw new Error(`site lists unknown task ${family}`);
    const cells = data.by_family_and_arm
      .filter((row) => row.task_family === family)
      .sort((a, b) => b.pass_rate - a.pass_rate);
    const plain = rendered.replace(/&gt;/g, ">").replace(/&#8776;|&asymp;/g, "≈");
    const separators = plain.match(/[>≈]/g) || [];
    if (separators.length !== cells.length - 1) {
      throw new Error(`${family}: expected ${cells.length - 1} separators, found ${separators.length}`);
    }
    cells.slice(1).forEach((cell, index) => {
      const tied = Math.abs(cells[index].passed - cell.passed) < 2;
      const wanted = tied ? "≈" : ">";
      if (separators[index] !== wanted) {
        throw new Error(`${family}: separator ${index + 1} should be ${tied ? "a tie" : "a rank"}`);
      }
    });
  }
  const width = data.expr_eval_width_failures;
  if (width.length !== 5) throw new Error("expected five integer-width rows");
'
if grep -q 'Agent time' docs/index.html docs/details.html; then
  echo "Elapsed time is published but this cohort ran concurrently." >&2
  exit 1
fi

grep -q 'result-chart' docs/index.html
grep -q 'footer-columns' docs/index.html
grep -q 'x.com/ubershmekel' docs/index.html
grep -q 'github.com/ubershmekel/language-ai-bench' docs/index.html

# The site loads v0.7 aggregates at runtime; stale study numbers must not linger in markup.
if grep -q '9/9' docs/index.html docs/details.html; then
  echo "Stale v0.6 per-language totals still present in the site markup." >&2
  exit 1
fi
grep -q 'Input tokens' docs/details.html
grep -q 'Technical details and paired uncertainty' docs/details.html
grep -q '"workflow_quality"' docs/data/decision-results.json

if grep -E -q 'hero-actions|Historical extension|What each language run cost' docs/index.html; then
  echo "Landing page contains removed or historical-first content." >&2
  exit 1
fi

if grep -R -q '—' README.md docs; then
  echo "Em dash found in public-facing copy." >&2
  exit 1
fi

if grep -R -E 'sk-or-v1-[A-Za-z0-9_-]{20,}' \
  docs/index.html docs/details.html docs/app.js docs/styles.css docs/data; then
  echo "Potential OpenRouter secret found in the public site." >&2
  exit 1
fi

echo "Public report validation passed."
