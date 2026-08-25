from scripts.audit_publication import audit


def test_detects_openrouter_key(tmp_path, monkeypatch):
    import scripts.audit_publication as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    path = tmp_path / "leak.txt"
    path.write_text("sk-" + "or-v1-" + "abcdefghijklmnopqrstuvwxyz123456")
    assert audit([path]) == ["leak.txt: OpenRouter key"]


def test_ordinary_text_is_clean(tmp_path, monkeypatch):
    import scripts.audit_publication as module

    monkeypatch.setattr(module, "ROOT", tmp_path)
    path = tmp_path / "report.txt"
    path.write_text("total cost: $0.13")
    assert audit([path]) == []
