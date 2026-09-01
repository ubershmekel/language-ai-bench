"""The published site must stay in step with the cohort JSON behind it."""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "publish_version.py"


def run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True
    )


def test_site_matches_the_published_cohort():
    assert run("--check").returncode == 0


def test_check_fails_when_the_page_drifts():
    """The failure this script exists to prevent: markup left behind by an edit."""
    index = ROOT / "docs" / "index.html"
    original = index.read_text(encoding="utf-8")
    marker = "<!-- generated:summary-rows -->"
    assert marker in original
    damaged = original.replace(
        marker, marker + "\n            <tr><td>Stale</td></tr>", 1
    )
    index.write_text(damaged, encoding="utf-8", newline="\n")
    try:
        result = run("--check")
        assert result.returncode == 1
        assert "stale" in result.stderr
    finally:
        index.write_text(original, encoding="utf-8", newline="\n")


def test_publishing_is_idempotent():
    before = {
        name: (ROOT / "docs" / name).read_text(encoding="utf-8")
        for name in ("index.html", "details.html", "app.js")
    }
    assert run().returncode == 0
    after = {
        name: (ROOT / "docs" / name).read_text(encoding="utf-8")
        for name in ("index.html", "details.html", "app.js")
    }
    assert before == after


def test_every_cohort_with_the_current_schema_can_be_rendered():
    """Rendering must not depend on fields only the newest cohort happens to have."""
    rendered = 0
    for path in sorted((ROOT / "docs" / "data").glob("v*-results.json")):
        report = json.loads(path.read_text(encoding="utf-8"))
        if "by_arm" not in report:
            continue
        assert report["by_family_and_arm"], path.name
        rendered += 1
    assert rendered >= 2


def test_older_schemas_are_refused_with_a_reason():
    result = run("--version", "v0.6")
    assert result.returncode != 0
    assert "predates the aggregate schema" in result.stderr
