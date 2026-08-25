import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_v06_report_is_complete_prospective_and_separate_from_history():
    report = json.loads((ROOT / "docs" / "data" / "v06-results.json").read_text())
    assert report["study_status"] == "complete-prospective"
    assert report["prospective"]["runs"] == 36
    assert report["prospective"]["passed"] == 36
    assert {row["runs"] for row in report["languages"]} == {9}
    assert len(report["cells"]) == 12
    assert {row["runs"] for row in report["cells"]} == {3}
    assert len(report["paired_contrasts"]) == 6
    assert {row["blocks"] for row in report["paired_contrasts"]} == {9}
    assert len(report["task_topology"]) == 12
    assert report["excluded_infrastructure"] == []
    assert "not pooled" in report["historical_boundary"]
    assert report["prospective"]["total_cost_usd"] < 0.75
    assert all(row["source_files"] > 0 and row["source_bytes"] > 0 for row in report["task_topology"])


def test_v06_public_outputs_exclude_private_identifiers():
    text = (ROOT / "docs" / "data" / "v06-results.json").read_text()
    markdown = (ROOT / "docs" / "V06_REPORT.md").read_text()
    for private in ("sk-or-", "API_KEY", "jobs/", "jobs\\", "result.json", "sample_seed", "order_index"):
        assert private not in text
        assert private not in markdown
    assert "20,000-resample paired bootstrap" in markdown
    assert "Earlier results remain historical" in markdown
