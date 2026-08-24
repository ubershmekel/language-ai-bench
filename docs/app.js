"use strict";

const resultName = (maturity, language) => `${maturity}-${language}`;

function formatMoney(value, digits = 6) {
  return `$${Number(value).toFixed(digits)}`;
}

function displayCondition(maturity) {
  return maturity === "brownfield" ? "Existing" : "New";
}

function displayLanguage(language) {
  return language === "javascript" ? "JavaScript" : "TypeScript";
}

function updateOverview(data) {
  const total = document.querySelector("#primary-total");
  if (total) total.textContent = String(data.primary.runs);

  for (const summary of data.maturity_summaries) {
    const output = document.querySelector(
      `[data-result="${resultName(summary.project_maturity, summary.language)}"]`,
    );
    if (output) output.textContent = `${summary.passed}/${summary.runs}`;
  }
}

function updateDetails(data) {
  const fields = {
    "#detail-runs": data.primary.runs,
    "#detail-passed": data.primary.passed,
    "#detail-cost": formatMoney(data.primary.total_cost_usd),
    "#detail-time": `${data.primary.mean_agent_seconds.toFixed(2)}s`,
  };

  for (const [selector, value] of Object.entries(fields)) {
    const element = document.querySelector(selector);
    if (element) element.textContent = String(value);
  }

  const body = document.querySelector("#details-results");
  if (!body) return;

  const order = { brownfield: 0, greenfield: 1, javascript: 0, typescript: 1 };
  const summaries = [...data.maturity_summaries].sort(
    (a, b) =>
      order[a.project_maturity] - order[b.project_maturity] ||
      order[a.language] - order[b.language],
  );

  body.replaceChildren(
    ...summaries.map((summary) => {
      const row = document.createElement("tr");
      const values = [
        displayCondition(summary.project_maturity),
        displayLanguage(summary.language),
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
  const response = await fetch("./data/decision-results.json", { cache: "no-cache" });
  if (!response.ok) throw new Error(`Aggregate request failed (${response.status})`);

  const data = await response.json();
  if (
    data.schema_version !== "1.0.0" ||
    !data.primary ||
    !Array.isArray(data.maturity_summaries)
  ) {
    throw new Error("Unsupported aggregate schema");
  }

  updateOverview(data);
  updateDetails(data);
}

loadResults().catch((error) => {
  console.error("Could not refresh checked aggregate values:", error);
});
