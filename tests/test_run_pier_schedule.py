import json

from scripts.run_pier_schedule import measured_trial, trial_results


def test_trial_results_and_measurement(tmp_path):
    trial = tmp_path / "job" / "date" / "trial"
    trial.mkdir(parents=True)
    (trial / "artifacts" / "workspace").mkdir(parents=True)
    result = {
        "agent_result": {"cost_usd": 0.0123},
        "verifier_result": {"rewards": {"reward": 1.0}},
        "exception_info": None,
    }
    path = trial / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")

    found = trial_results(tmp_path)
    assert found == {path: result}
    measurement = measured_trial(path, result)
    assert measurement["cost_usd"] == 0.0123
    assert measurement["reward"] == 1.0
    assert measurement["workspace_artifact_captured"] is True


def test_exceptional_trial_is_measured_and_labelled(tmp_path):
    trial = tmp_path / "job" / "date" / "trial"
    trial.mkdir(parents=True)
    result = {
        "agent_result": {"cost_usd": 0.001},
        "verifier_result": {"rewards": {"reward": 0.0}},
        "exception_info": {"exception_type": "NonZeroAgentExitCodeError"},
    }
    path = trial / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")

    measurement = measured_trial(path, result)
    assert measurement["exception_type"] == "NonZeroAgentExitCodeError"
    assert measurement["workspace_artifact_captured"] is False
