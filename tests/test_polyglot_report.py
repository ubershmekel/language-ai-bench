import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_checked_public_report_is_balanced_and_records_exclusion():
    report = json.loads((ROOT / "docs" / "data" / "polyglot-results.json").read_text())
    assert report["balanced_polyglot"]["runs"] == 20
    assert report["balanced_polyglot"]["passed"] == 20
    assert report["all_published"]["runs"] == 32
    assert len(report["excluded_infrastructure"]) == 1
    assert report["excluded_infrastructure"][0]["classification"] == "pre-submission-infrastructure"
    assert {row["runs"] for row in report["polyglot_languages"]} == {5}
    assert {(row["task_family"], row["runs"]) for row in report["polyglot_cells"]} == {
        ("optimistic-concurrency", 2),
        ("schedule-variants", 3),
    }
    markdown = (ROOT / "docs" / "POLYGLOT_REPORT.md").read_text()
    assert "20 valid attempts" in markdown
    assert "32 valid completions" in markdown
    assert "egress proxy" in markdown