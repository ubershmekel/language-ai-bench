#!/usr/bin/env python3
"""Regenerate every part of the site that is derived from a cohort's results.

The site used to be updated by hand after each cohort, and v1.0 shipped with the
landing page still fetching the previous cohort's JSON and `details.html` still
holding numbers from two cohorts before that. Anything derived from the results
belongs to this script now, inside `<!-- generated:name -->` markers.

    python3 scripts/publish_version.py --version v1.0     # rewrite
    python3 scripts/publish_version.py --check            # fail if stale

`--check` regenerates into memory and compares, so a page that drifts from its
data fails the gate instead of being served. It is what `validate-pages.sh`
runs. With no `--version` the script publishes the newest `docs/data/*-results.json`.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "data"
INDEX = ROOT / "docs" / "index.html"
DETAILS = ROOT / "docs" / "details.html"
APP = ROOT / "docs" / "app.js"

ARMS = ("javascript", "typescript", "python", "python-typed", "go")
LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "python": "Python",
    "python-typed": "Python (typed)",
    "go": "Go",
}
# The landing page writes "Python typed" without the parentheses.
SHORT = dict(LABELS, **{"python-typed": "Python typed"})
CHECKING = {
    "javascript": "None",
    "typescript": "Strict",
    "python": "None",
    "python-typed": "mypy strict",
    "go": "Compiler",
}
# Two setups within this many runs of each other are shown as tied. Eight
# attempts cannot separate them, and a ">" would read as a ranking.
TIE_RUNS = 2


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def slug_of(version: str) -> str:
    """v1.0 -> v10, matching the docs/data file names."""
    return "v" + version.lstrip("v").replace(".", "")


def version_of(slug: str) -> str:
    digits = slug.lstrip("v")
    return f"v{digits[0]}.{digits[1:]}"


def cohorts() -> list[str]:
    """Every published cohort slug, oldest first."""
    found = []
    for path in DATA.glob("v*-results.json"):
        match = re.fullmatch(r"(v\d+)-results", path.stem)
        if match:
            found.append(match.group(1))
    return sorted(found, key=lambda slug: [int(part) for part in version_of(slug).lstrip("v").split(".")])


def replace_region(text: str, name: str, body: str) -> str:
    pattern = re.compile(
        rf"(<!-- generated:{re.escape(name)} -->\n?).*?(\n?[ ]*<!-- /generated:{re.escape(name)} -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"missing generated region: {name}")
    return pattern.sub(lambda match: match.group(1) + body + match.group(2), text, count=1)


def ordered(report: dict) -> list[dict]:
    by_language = {cell["language"]: cell for cell in report["by_arm"]}
    return [by_language[arm] for arm in ARMS if arm in by_language]


def task_orderings(report: dict) -> list[tuple[str, list[dict]]]:
    families: dict[str, list[dict]] = {}
    for cell in report["by_family_and_arm"]:
        families.setdefault(cell["task_family"], []).append(cell)
    rows = []
    for family, cells in families.items():
        passed = [cell["passed"] for cell in cells]
        rows.append(
            (
                family,
                max(passed) - min(passed),
                sorted(cells, key=lambda cell: (-cell["pass_rate"], cell["language"])),
            )
        )
    rows.sort(key=lambda row: (-row[1], row[0]))
    return [(family, order) for family, _, order in rows]


def render_index(report: dict, slug: str, version: str, previous: str | None) -> dict[str, str]:
    arms = ordered(report)
    regions = {
        "chart-pass": '          <p class="chart-fallback">'
        + " &middot; ".join(f"{SHORT[c['language']]} {c['passed']}/{c['runs']}" for c in arms)
        + "</p>",
        "chart-steps": '          <p class="chart-fallback">'
        + " &middot; ".join(f"{SHORT[c['language']]} {c['mean_agent_steps']:.2f}" for c in arms)
        + "</p>",
        "chart-cost": '          <p class="chart-fallback">'
        + " &middot; ".join(f"{SHORT[c['language']]} ${c['mean_cost_usd']:.4f}" for c in arms)
        + "</p>",
    }

    rows = "\n".join(
        f"            <tr><td>{LABELS[c['language']]}</td><td>{CHECKING[c['language']]}</td>"
        f"<td>{c['passed']}/{c['runs']}</td><td>{c['mean_agent_steps']:.2f}</td>"
        f"<td>{c['mean_output_tokens']:,.0f}</td><td>${c['mean_cost_usd']:.6f}</td></tr>"
        for c in arms
    )
    regions["summary-rows"] = (
        '          <tbody id="language-summary-results">\n' + rows + "\n          </tbody>"
    )

    items = []
    for family, order in task_orderings(report):
        pieces = []
        for index, cell in enumerate(order):
            if index:
                tied = abs(order[index - 1]["passed"] - cell["passed"]) < TIE_RUNS
                pieces.append(" &#8776; " if tied else " &gt; ")
            pieces.append(f"{LABELS[cell['language']]} {cell['passed']}/{cell['runs']}")
        items.append(f"        <li><code>{family}</code> " + "".join(pieces) + "</li>")
    regions["task-orderings"] = (
        '      <ul id="family-reversal" class="family-reversal">\n'
        + "\n".join(items)
        + "\n      </ul>"
    )

    links = [
        f'        <a href="./{slug.upper()}_REPORT.md">Current report ({version})</a>',
        f'        <a href="./data/{slug}-results.json">Aggregate data (JSON)</a>',
        '        <a href="./details.html">Technical details</a>',
    ]
    if previous:
        links.append(
            f'        <a href="./{previous.upper()}_REPORT.md">'
            f"Previous study ({version_of(previous)})</a>"
        )
    links += [
        '        <a href="./POLYGLOT_REPORT.md">Earlier study (v0.5)</a>',
        '        <a href="./DESIGN.md">Experimental design</a>',
    ]
    regions["report-links"] = "\n".join(links)
    return regions


def render_details(report: dict, slug: str, previous: str | None) -> dict[str, str]:
    arms = ordered(report)
    rows = "\n".join(
        f"            <tr><td>{LABELS[c['language']]}</td><td>{c['passed']}/{c['runs']}</td>"
        f"<td>${c['mean_cost_usd']:.6f}</td><td>{c['mean_input_tokens']:,.0f}</td>"
        f"<td>{c['mean_output_tokens']:,.0f}</td><td>{c['mean_agent_steps']:.2f}</td></tr>"
        for c in arms
    )
    passed = sum(cell["passed"] for cell in report["by_arm"])
    excluded = len(report.get("excluded_infrastructure_failures", []))
    stats = "\n".join(
        [
            f'        <div><span>Attempts</span><strong id="detail-runs">{report["rollouts"]}</strong></div>',
            f'        <div><span>Passed</span><strong id="detail-passed">{passed}</strong></div>',
            f'        <div><span>API spend</span><strong id="detail-cost">${report["total_cost_usd"]:.6f}</strong></div>',
            f"        <div><span>Infrastructure failures</span><strong>{excluded}</strong></div>",
        ]
    )
    previous_link = (
        f'<a href="./{previous.upper()}_REPORT.md">Previous report</a>' if previous else ""
    )
    return {
        "details-rows": '          <tbody id="details-results">\n' + rows + "\n          </tbody>",
        "details-stats": stats,
        "details-nav": f'<a href="./data/{slug}-results.json">Latest aggregates</a>',
        "details-links": (
            f'<a href="./data/{slug}-results.json">Latest aggregate JSON</a>'
            f'<a href="./{slug.upper()}_REPORT.md">Latest written report</a>'
            '<a href="./methodology.html">How scoring works</a>'
            + previous_link
        ),
    }


def rewrite(paths: dict[pathlib.Path, str]) -> list[pathlib.Path]:
    changed = []
    for path, text in paths.items():
        if path.read_text(encoding="utf-8") != text:
            changed.append(path)
    return changed


def build(slug: str) -> dict[pathlib.Path, str]:
    results = DATA / f"{slug}-results.json"
    if not results.is_file():
        raise SystemExit(f"no aggregate JSON at {results.relative_to(ROOT)}")
    report = load(results)
    # v0.6 and v0.7 predate the per-arm aggregate shape the site renders.
    missing = [key for key in ("by_arm", "by_family_and_arm") if key not in report]
    if missing:
        raise SystemExit(
            f"{results.name} predates the aggregate schema the site renders "
            f"(no {', '.join(missing)}); it cannot be published"
        )
    version = version_of(slug)
    published = cohorts()
    index = published.index(slug) if slug in published else len(published)
    previous = published[index - 1] if index > 0 else None

    index_text = INDEX.read_text(encoding="utf-8")
    for name, body in render_index(report, slug, version, previous).items():
        index_text = replace_region(index_text, name, body)

    details_text = DETAILS.read_text(encoding="utf-8")
    for name, body in render_details(report, slug, previous).items():
        details_text = replace_region(details_text, name, body)

    app_text = re.sub(
        r'fetch\("\./data/v\d+-results\.json"',
        f'fetch("./data/{slug}-results.json"',
        APP.read_text(encoding="utf-8"),
        count=1,
    )
    return {INDEX: index_text, DETAILS: details_text, APP: app_text}


def regenerate_report(slug: str) -> None:
    """Rebuild the aggregate JSON and the written report from the run ledger.

    The ledger is private and gitignored, so this only works on the machine that
    ran the cohort. Everywhere else the committed JSON is the input.
    """
    generator = ROOT / "analysis" / f"{slug}_report.py"
    if not generator.is_file():
        raise SystemExit(f"no report generator at {generator.relative_to(ROOT)}")
    command = [
        sys.executable,
        str(generator),
        "--json-output",
        str(DATA / f"{slug}-results.json"),
        "--markdown-output",
        str(ROOT / "docs" / f"{slug.upper()}_REPORT.md"),
    ]
    finished = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    if finished.returncode != 0:
        sys.stderr.write(finished.stderr)
        raise SystemExit(f"{generator.name} failed; is the run ledger present?")
    print(f"rebuilt docs/data/{slug}-results.json and docs/{slug.upper()}_REPORT.md")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        help="cohort to publish, for example v1.0. Defaults to the newest published.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit nonzero if any page is stale",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help=(
            "first rebuild the cohort's aggregate JSON and written report from "
            "its ledger. Only works where the run happened: ledgers are private."
        ),
    )
    args = parser.parse_args()

    published = cohorts()
    if not published and not args.report:
        raise SystemExit("no docs/data/v*-results.json to publish")
    slug = slug_of(args.version) if args.version else published[-1]

    if args.report:
        regenerate_report(slug)

    wanted = build(slug)
    stale = rewrite(wanted)
    if args.check:
        if stale:
            for path in stale:
                print(f"stale: {path.relative_to(ROOT)}", file=sys.stderr)
            print(
                f"run: python3 scripts/publish_version.py --version {version_of(slug)}",
                file=sys.stderr,
            )
            return 1
        print(f"site is current for {version_of(slug)}")
        return 0

    for path, text in wanted.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    if stale:
        for path in stale:
            print(f"updated {path.relative_to(ROOT)}")
    else:
        print(f"already current for {version_of(slug)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
