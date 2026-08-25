"use strict";

const resultName = (maturity, language) => `${maturity}-${language}`;
const languageLabels = {
  javascript: "JavaScript",
  typescript: "TypeScript",
  python: "Python",
  go: "Go",
};

function formatMoney(value, digits = 6) {
  return `$${Number(value).toFixed(digits)}`;
}

function displayCondition(summary) {
  const base = summary.project_maturity === "brownfield" ? "Existing" : "New";
  return summary.interpretation === "illustrative_single_run" ? `${base} · example` : base;
}

function updateResult(summary) {
  const output = document.querySelector(
    `[data-result="${resultName(summary.project_maturity, summary.language)}"]`,
  );
  if (output) output.textContent = `${summary.passed}/${summary.runs}`;
}

function updateLanguageSummary(data) {
  const body = document.querySelector("#language-summary-results");
  if (!body) return;

  const languageOrder = { javascript: 0, typescript: 1, python: 2, go: 3 };
  const source = data.languages || data.polyglot_languages || data.language_summaries;
  const summaries = [...source].sort(
    (a, b) => languageOrder[a.language] - languageOrder[b.language],
  );

  body.replaceChildren(
    ...summaries.map((summary) => {
      const row = document.createElement("tr");
      if (summary.interpretation === "illustrative_single_run") {
        row.classList.add("illustrative-row");
      }
      const isProspective = Array.isArray(data.languages);
      const isPolyglot = Array.isArray(data.polyglot_languages);
      const isBalanced = summary.interpretation === "balanced_primary";
      const evidence = isProspective
        ? summary.runs + " runs · 3 existing tasks"
        : isPolyglot
          ? summary.runs + " runs · 2 existing tasks"
        : isBalanced
          ? summary.runs + " runs · new + existing"
          : summary.runs + " example · existing";
      const values = [
        languageLabels[summary.language],
        evidence,
        summary.passed + "/" + summary.runs,
        formatMoney(summary.mean_cost_usd),
        Math.round(summary.mean_input_tokens).toLocaleString("en-US"),
        Math.round(summary.mean_output_tokens).toLocaleString("en-US"),
        summary.mean_agent_steps.toFixed(2),
        summary.mean_agent_seconds.toFixed(2) + "s",
      ];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }),
  );
}

function updateOverview(data) {
  const total = document.querySelector("#primary-total");
  if (total) total.textContent = String(data.primary.runs);
  data.maturity_summaries.forEach(updateResult);
  data.polyglot_examples.forEach(updateResult);
  updateLanguageSummary(data);
}

function updateDetails(data) {
  const published = data.prospective || data.all_published;
  const fields = {
    "#detail-runs": published.runs,
    "#detail-passed": published.passed,
    "#detail-cost": formatMoney(data.total_measured_spend_usd || published.total_cost_usd),
    "#detail-time": `${published.mean_agent_seconds.toFixed(2)}s`,
  };

  for (const [selector, value] of Object.entries(fields)) {
    const element = document.querySelector(selector);
    if (element) element.textContent = String(value);
  }

  const body = document.querySelector("#details-results");
  if (!body) return;

  const languageOrder = { javascript: 0, typescript: 1, python: 2, go: 3 };
  const summaries = data.languages
    ? [...data.languages].sort((a, b) => languageOrder[a.language] - languageOrder[b.language])
    : data.polyglot_languages
      ? [...data.polyglot_languages].sort((a, b) => languageOrder[a.language] - languageOrder[b.language])
    : [...data.maturity_summaries, ...data.polyglot_examples].sort(
        (a, b) =>
          (a.project_maturity === "brownfield" ? 0 : 1) -
            (b.project_maturity === "brownfield" ? 0 : 1) ||
          languageOrder[a.language] - languageOrder[b.language],
      );

  body.replaceChildren(
    ...summaries.map((summary) => {
      const row = document.createElement("tr");
      const values = [
        data.languages ? "3 existing tasks" : displayCondition(summary),
        languageLabels[summary.language],
        `${summary.passed}/${summary.runs}`,
        formatMoney(summary.mean_cost_usd),
        Math.round(summary.mean_output_tokens).toLocaleString("en-US"),
        summary.mean_agent_steps.toFixed(2),
        `${summary.mean_agent_seconds.toFixed(2)}s`,
      ];
      for (const value of values) {
        const cell = document.createElement("td");
        cell.textContent = value;
        row.append(cell);
      }
      return row;
    }),
  );
}

async function loadResults() {
  const response = await fetch("./data/v06-results.json", { cache: "no-cache" });
  if (!response.ok) throw new Error(`Aggregate request failed (${response.status})`);

  const data = await response.json();
  if (
    data.schema_version !== "1.0.0" ||
    !data.prospective ||
    !Array.isArray(data.languages) ||
    !Array.isArray(data.cells) ||
    !Array.isArray(data.paired_contrasts)
  ) {
    throw new Error("Unsupported aggregate schema");
  }

  updateLanguageSummary(data);
  updateDetails(data);
}

loadResults().catch((error) => {
  console.error("Could not refresh checked aggregate values:", error);
});
