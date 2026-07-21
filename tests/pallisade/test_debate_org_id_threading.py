from pallisade_worker.debate_runner import _build_config


def test_build_config_copies_org_id():
    cfg = _build_config({"org_id": "org-123", "trade_date": "2026-07-20"})
    assert cfg["org_id"] == "org-123"


def test_build_config_org_id_absent_is_fine():
    cfg = _build_config({"trade_date": "2026-07-20"})
    assert cfg.get("org_id") is None
