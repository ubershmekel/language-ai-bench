from scripts.audit_task_integrity import audit


def test_task_integrity():
    assert audit() == []
