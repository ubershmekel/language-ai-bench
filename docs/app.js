"use strict";

const formatPercent = (value, digits = 1) => `${(value * 100).toFixed(digits)}%`;
const formatMoney = (value, digits = 4) => `$${value.toFixed(digits)}`;
const formatNumber = (value, digits = 0) => value.toFixed(digits);
const escapeHtml = (value) =>
  String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);

const metrics = [
  { label: "Pass rate", key: "pass_rate", format: (value) => formatPercent(value, 0) },
  { label: "Mean cost", key: "mean_cost_usd", format: formatMoney },
  { label: "Output tokens", key: "mean_output_tokens", format: (value) => formatNumber(value) },
  { label: "Agent steps", key: "mean_agent_steps", format: (value) => formatNumber(value, 2) },
  { label: "Agent time", key: "mean_agent_seconds", format: (value) => `${formatNumber(value, 2)}s` },
];

function metricCell(summary, metric, isTypeScript, max) {
  const width = max === 0 ? 0 : Math.max(3, (summary[metric.key] / max) * 100);
  return `
    <div class="metric-value">
      ${escapeHtml(metric.format(summary[metric.key]))}
      <div class="bar-track" aria-hidden="true">
        <div class="bar${isTypeScript ? " ts" : ""}" style="width:${width.toFixed(1)}%"></div>
      </div>
    </div>`;
}

function renderPanel(maturity, summaries, contrast) {
  const javascript = summaries.find((row) => row.language === "javascript");
  const typescript = summaries.find((row) => row.language === "typescript");
  if (!javascript || !typescript) throw new Error(`Missing language summary for ${maturity}`);

  const rows = metrics.map((metric) => {
    const max = Math.max(javascript[metric.key], typescript[metric.key]);
    return `
      <div class="metric-label">${escapeHtml(metric.label)}</div>
      ${metricCell(javascript, metric, false, max)}
      ${metricCell(typescript, metric, true, max)}`;
  }).join("");

  const signed = (value) => `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
  return `
    <article class="comparison-panel">
      <div class="panel-top">
        <h3>${escapeHtml(maturity)} project</h3>
        <p>${javascript.runs + typescript.runs} balanced runs · identical pass rate</p>
      </div>
      <div class="language-grid">
        <span></span>
        <div class="language-head"><strong>JavaScript</strong><span>${javascript.passed}/${javascript.runs} passed</span></div>
        <div class="language-head ts"><strong>TypeScript</strong><span>${typescript.passed}/${typescript.runs} passed</span></div>
        ${rows}
        <div class="delta-row" aria-label="TypeScript relative to JavaScript">
          <span class="delta good">steps ${signed(contrast.typescript_relative_mean_steps_percent)}</span>
          <span class="delta good">output ${signed(contrast.typescript_relative_mean_output_percent)}</span>
          <span class="delta good">cost ${signed(contrast.typescript_relative_mean_cost_percent)}</span>
          <span class="delta slower">time ${signed(contrast.typescript_relative_mean_agent_seconds_percent)}</span>
        </div>
      </div>
    </article>`;
}

function updateSummary(data) {
  const primary = data.primary;
  document.querySelector("#primary-passes").textContent = `${primary.passed}/${primary.runs}`;
  document.querySelector("#primary-rate").textContent = `${formatPercent(primary.pass_rate, 0)} pass rate`;
  document.querySelector("#primary-cost").textContent = formatMoney(primary.total_cost_usd);
  document.querySelector("#primary-cache").textContent = formatPercent(primary.cache_hit_rate);

  const contrasts = data.contrasts;
  const absoluteRange = (key) => {
    const values = contrasts.map((row) => Math.abs(row[key]));
    return `${Math.round(Math.min(...values))}–${Math.round(Math.max(...values))}%`;
  };
  document.querySelector("#step-range").textContent = absoluteRange("typescript_relative_mean_steps_percent");
  document.querySelector("#output-range").textContent = absoluteRange("typescript_relative_mean_output_percent");
  document.querySelector("#time-range").textContent = absoluteRange("typescript_relative_mean_agent_seconds_percent");

  const generated = new Date(data.generated_at);
  document.querySelector("#generated-at").textContent =
    `Aggregate generated ${generated.toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric", timeZone: "UTC" })}`;
}

async function renderReport() {
  const response = await fetch("./data/decision-results.json", { cache: "no-cache" });
  if (!response.ok) throw new Error(`Aggregate request failed (${response.status})`);
  const data = await response.json();
  if (data.schema_version !== "1.0.0" || !Array.isArray(data.maturity_summaries)) {
    throw new Error("Unsupported aggregate schema");
  }

  updateSummary(data);
  const maturities = ["brownfield", "greenfield"];
  document.querySelector("#comparison-panels").innerHTML = maturities.map((maturity) => {
    const summaries = data.maturity_summaries.filter((row) => row.project_maturity === maturity);
    const contrast = data.contrasts.find((row) => row.project_maturity === maturity);
    if (!contrast) throw new Error(`Missing contrast for ${maturity}`);
    return renderPanel(maturity, summaries, contrast);
  }).join("");
}

renderReport().catch((error) => {
  console.error(error);
  document.querySelector("#comparison-panels").innerHTML = `
    <p class="loading">The interactive comparison could not load. Read the
    <a href="./DECISION_REPORT.md"><u>checked report</u></a> instead.</p>`;
});
