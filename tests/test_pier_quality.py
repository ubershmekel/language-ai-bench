from analysis.pier_quality import extract


def action(step_id, command, returncode=0):
    return {
        "step_id": step_id,
        "source": "agent",
        "tool_calls": [{"arguments": {"command": command}}],
        "observation": {"results": [{"content": {"returncode": returncode}}]},
    }


def test_extracts_first_pass_and_submit_order():
    trajectory = {"steps": [
        action(1, "sed -i 's/a/b/' src/server.ts"),
        action(2, "npm run typecheck"),
        action(3, "scripts/verify-local"),
        action(4, "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"),
    ]}
    result = {"verifier_result": {"rewards": {"reward": 1.0}}, "agent_result": {"cost_usd": 0.01}}
    quality = extract(trajectory, result)
    assert quality["hidden_test_pass"] is True
    assert quality["first_developer_verification_pass"] is True
    assert quality["passing_developer_verification_before_submit"] is True
    assert quality["verification_attempts"] == 1
    assert quality["static_check_invocations"] == 1
    assert quality["edit_command_invocations"] == 1
    assert quality["patch_statistics"]["files_changed"] is None


def test_does_not_claim_missing_verification_or_patch_data():
    quality = extract({"steps": [action(1, "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT")]})
    assert quality["first_developer_verification_pass"] is None
    assert quality["developer_verification_before_submit"] is False
    assert quality["hidden_test_pass"] is None
    assert quality["review_findings"] is None
