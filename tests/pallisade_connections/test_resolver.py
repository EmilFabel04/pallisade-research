from __future__ import annotations

from pallisade_connections.models import DataConnection
from pallisade_connections.resolver import resolve_for_org


def test_nothing_connected_falls_back_to_yfinance(db, make_user):
    user = make_user(role="admin")
    resolved = resolve_for_org(db, user.org_id)
    assert "yfinance" in resolved.registry
    assert "yfinance" in resolved.client_config.enabled_sources


def test_eodhd_is_always_on(db, make_user):
    user = make_user(role="admin")
    resolved = resolve_for_org(db, user.org_id)
    assert "eodhd" in resolved.registry
    assert "eodhd" in resolved.client_config.enabled_sources
    assert "gdelt" not in resolved.registry


def test_markets_and_macro_always_on(db, make_user):
    user = make_user(role="admin")
    resolved = resolve_for_org(db, user.org_id)
    assert {"worldbank", "eodhd_markets"} <= set(resolved.registry)


def test_connected_source_is_enabled(db, make_user, enc_key):
    from pallisade_connections.crypto import encrypt
    user = make_user(role="admin")
    db.add(DataConnection(
        org_id=user.org_id, connector_type="smartkarma", label="SK",
        status="connected", credentials_encrypted=encrypt("sk-key"),
        serves=["research"], created_by=user.id, config_json={},
    ))
    db.flush()
    resolved = resolve_for_org(db, user.org_id)
    assert "smartkarma" in resolved.registry
    assert "smartkarma" in resolved.client_config.enabled_sources


def test_disconnected_source_is_excluded(db, make_user):
    user = make_user(role="admin")
    db.add(DataConnection(
        org_id=user.org_id, connector_type="smartkarma", label="SK",
        status="disconnected", serves=["research"], created_by=user.id, config_json={},
    ))
    db.flush()
    resolved = resolve_for_org(db, user.org_id)
    assert "smartkarma" not in resolved.registry
