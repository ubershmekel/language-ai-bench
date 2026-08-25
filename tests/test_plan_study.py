import json
import pathlib

from scripts.plan_study import build_schedule, validate

ROOT = pathlib.Path(__file__).resolve().parents[1]


def study():
    return json.loads((ROOT / "study_v0.5.json").read_text(encoding="utf-8"))


def test_design_is_valid_but_not_launch_ready():
    value = study()
    assert validate(value) == []
    errors = validate(value, require_launch_ready=True)
    assert "study status is not ready" in errors
    assert "launch requires at least three ready task families" not in errors


def test_schedule_is_deterministic_and_balanced():
    value = study()
    first = build_schedule(value)
    assert first == build_schedule(value)
    expected = value["attempts_per_cell"]
    counts = {}
    for row in first:
        key = (row["task_family"], row["language"])
        counts[key] = counts.get(key, 0) + 1
    assert set(counts.values()) == {expected}
    assert [row["order_index"] for row in first] == list(range(1, len(first) + 1))
