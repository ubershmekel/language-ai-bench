"use strict";

const languageLabels = {
  javascript: "JavaScript",
  typescript: "TypeScript",
  python: "Python",
  "python-typed": "Python (typed)",
  go: "Go",
};
const languageOrder = {
  javascript: 0,
  typescript: 1,
  python: 2,
  "python-typed": 3,
  go: 4,
};
const languageColors = {
  javascript: "var(--yellow)",
  typescript: "var(--blue)",
  python: "#6eb6dc",
  "python-typed": "#4f9bc4",
  go: "#77d5e9",
};
const typeChecking = {
  javascript: "None",
  typescript: "Strict",
  python: "None",
  "python-typed": "mypy strict",
  go: "Compiler",
};

function formatMoney(value, digits = 6) {
  return `$${Number(value).toFixed(digits)}`;
}

function ordered(rows) {
  return [...rows].sort(
    (a, b) => languageOrder[a.language] - languageOrder[b.language],
  );
}

/**
 * Families ranked by arm, best first, skipping any too flat to rank. A single
 * run of separation out of eight is not an ordering, so requiring two keeps
 * saturated families from being drawn as though they said something.
 */
const MINIMUM_SPREAD_RUNS = 2;

function discriminatingFamilies(data) {
  const families = new Map();
  for (const cell of data.by_family_and_arm) {
    if (!families.has(cell.task_family)) families.set(cell.task_family, []);
    families.get(cell.task_family).push(cell);
  }
  const result = [];
  for (const [family, cells] of families) {
    const passed = cells.map((cell) => cell.passed);
    if (Math.max(...passed) - Math.min(...passed) < MINIMUM_SPREAD_RUNS) continue;
    result.push({
      family,
      order: [...cells].sort((a, b) => b.pass_rate - a.pass_rate),
    });
  }
  return result.sort((a, b) => a.family.localeCompare(b.family));
}

function fillRows(selector, rows, cells) {
  const body = document.querySelector(selector);
  if (!body) return;
  body.replaceChildren(
    ...rows.map((row) => {
      const element = document.createElement("tr");
      for (const value of cells(row)) {
        const cell = document.createElement("td");
        cell.textContent = value;
        element.append(cell);
      }
      return element;
    }),
  );
}

function updateLanguageSummary(data) {
  fillRows("#language-summary-results", ordered(data.by_arm), (row) => [
    languageLabels[row.language],
    typeChecking[row.language],
    `${row.passed}/${row.runs}`,
    row.mean_agent_steps.toFixed(2),
    Math.round(row.mean_output_tokens).toLocaleString("en-US"),
    formatMoney(row.mean_cost_usd),
  ]);
}

function updateDetailsTable(data) {
  fillRows("#details-results", ordered(data.by_arm), (row) => [
    languageLabels[row.language],
    `${row.passed}/${row.runs}`,
    formatMoney(row.mean_cost_usd),
    Math.round(row.mean_input_tokens).toLocaleString("en-US"),
    Math.round(row.mean_output_tokens).toLocaleString("en-US"),
    row.mean_agent_steps.toFixed(2),
  ]);
}

function svg(name, attributes, children = []) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) {
    node.setAttribute(key, String(value));
  }
  node.append(...children);
  return node;
}

/**
 * One panel of horizontal bars. `rows` carry a value, an optional interval, and
 * a preformatted label so the caller decides units.
 */
function barPanel(title, subtitle, rows, maximum) {
  const rowHeight = 44;
  const labelWidth = 96;
  const valueWidth = 74;
  const width = 500;
  const height = rows.length * rowHeight + 8;
  const trackStart = labelWidth;
  const trackWidth = width - labelWidth - valueWidth;

  const children = [];
  rows.forEach((row, index) => {
    const middle = index * rowHeight + rowHeight / 2;
    const length = maximum ? Math.max((row.value / maximum) * trackWidth, 2) : 2;
    children.push(
      svg("text", {
        x: 0,
        y: middle + 4,
        fill: "var(--muted)",
        "font-size": "13",
      }, [document.createTextNode(row.label)]),
    );
    children.push(
      svg("rect", {
        x: trackStart,
        y: middle - 11,
        width: trackWidth,
        height: 22,
        rx: 4,
        fill: "var(--surface-2)",
      }),
    );
    children.push(
      svg("rect", {
        x: trackStart,
        y: middle - 11,
        width: length,
        height: 22,
        rx: 4,
        fill: row.color,
      }),
    );
    if (row.interval && maximum) {
      const low = trackStart + (row.interval[0] / maximum) * trackWidth;
      const high = trackStart + (row.interval[1] / maximum) * trackWidth;
      children.push(
        svg("line", {
          x1: low, x2: high, y1: middle, y2: middle,
          stroke: "var(--ink)", "stroke-width": 1.5, opacity: 0.55,
        }),
      );
      for (const x of [low, high]) {
        children.push(
          svg("line", {
            x1: x, x2: x, y1: middle - 5, y2: middle + 5,
            stroke: "var(--ink)", "stroke-width": 1.5, opacity: 0.55,
          }),
        );
      }
    }
    children.push(
      svg("text", {
        x: width,
        y: middle + 4,
        fill: "var(--ink)",
        "font-size": "13",
        "text-anchor": "end",
        "font-variant-numeric": "tabular-nums",
      }, [document.createTextNode(row.display)]),
    );
  });

  const figure = document.createElement("figure");
  figure.className = "chart-panel";
  const caption = document.createElement("figcaption");
  caption.innerHTML = `<strong>${title}</strong><span>${subtitle}</span>`;
  figure.append(
    caption,
    svg("svg", {
      viewBox: `0 0 ${width} ${height}`,
      width: "100%",
      role: "img",
      "aria-label": `${title}. ${rows.map((row) => `${row.label} ${row.display}`).join(". ")}`,
    }, children),
  );
  return figure;
}

function renderChart(data) {
  const host = document.querySelector("#result-chart");
  if (!host) return;
  const rows = ordered(data.by_arm);

  const passRows = rows.map((row) => ({
    label: languageLabels[row.language],
    color: languageColors[row.language],
    value: row.pass_rate,
    interval: row.pass_rate_ci95,
    display: `${row.passed}/${row.runs}`,
  }));

  const stepRows = rows.map((row) => ({
    label: languageLabels[row.language],
    color: languageColors[row.language],
    value: row.mean_agent_steps,
    display: row.mean_agent_steps.toFixed(2),
  }));
  const stepMaximum = Math.max(...stepRows.map((row) => row.value)) * 1.15;

  host.replaceChildren(
    barPanel(
      "Did it succeed?",
      "Share of attempts passing the hidden verifier, with 95% intervals. Higher is better.",
      passRows,
      1,
    ),
    barPanel(
      "How much work did it take?",
      "Mean agent steps per attempt: how much work the same result took. Lower is better.",
      stepRows,
      stepMaximum,
    ),
  );
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = String(value);
}

function updateHeadlineNumbers(data) {
  const passed = data.by_arm.reduce((total, row) => total + row.passed, 0);
  setText("#stat-passed", `${passed}/${data.rollouts}`);
  const perArm = ordered(data.by_arm)[0];
  setText("#stat-runs", perArm ? perArm.runs : data.rollouts);
  setText("#stat-spend", formatMoney(data.total_cost_usd, 2));
  setText("#detail-runs", data.rollouts);
  setText("#detail-passed", passed);
  setText("#detail-cost", formatMoney(data.total_cost_usd));

  const primary = data.primary_contrast.estimates.hidden_test_pass;
  const [low, high] = primary.ci95;
  const sign = primary.mean_difference >= 0 ? "+" : "";
  setText(
    "#primary-contrast",
    `${sign}${primary.mean_difference.toFixed(3)} (95% CI ${low.toFixed(3)} to ${high.toFixed(3)})`,
  );
}

/** The orderings, rendered so the reversal is visible rather than described. */
function renderFamilyReversal(data) {
  const host = document.querySelector("#family-reversal");
  if (!host) return;
  host.replaceChildren(
    ...discriminatingFamilies(data).map((item) => {
      const row = document.createElement("li");
      const name = document.createElement("code");
      name.textContent = item.family;
      const order = document.createElement("span");
      order.textContent = ` ${item.order
        .map((cell) => `${languageLabels[cell.language]} ${cell.passed}/${cell.runs}`)
        .join(" > ")}`;
      row.append(name, order);
      return row;
    }),
  );
}

async function loadResults() {
  const response = await fetch("./data/v09-results.json", { cache: "no-cache" });
  if (!response.ok) throw new Error(`Aggregate request failed (${response.status})`);

  const data = await response.json();
  if (
    data.schema_version !== "1.0.0" ||
    !Array.isArray(data.by_arm) ||
    !Array.isArray(data.by_family_and_arm) ||
    !data.primary_contrast
  ) {
    throw new Error("Unsupported aggregate schema");
  }

  updateLanguageSummary(data);
  updateDetailsTable(data);
  updateHeadlineNumbers(data);
  renderChart(data);
  renderFamilyReversal(data);
}

loadResults().catch((error) => {
  console.error("Could not refresh checked aggregate values:", error);
});
