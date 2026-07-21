from __future__ import annotations

from pallisade_connections.models import DataConnection, Organization, default_org_id


def test_default_org_exists(db):
    org = db.get(Organization, default_org_id(db))
    assert org is not None
    assert org.name == "Pallisade"


def test_new_user_gets_default_org(db):
    from pallisade_core.users import service as users_service
    u = users_service.create_user(
        db, email="orgtest@example.com", name="Org Test",
        role="member", password="TestPass!12345", must_change_password=False,
    )
    db.flush()
    assert u.org_id == default_org_id(db)


def test_data_connection_persists(db, make_user):
    user = make_user(role="admin")
    conn = DataConnection(
        org_id=user.org_id, connector_type="mcp", label="EODHD",
        status="disconnected", config_json={"endpoint_url": "https://x"},
        serves=["fundamentals", "news"], created_by=user.id,
    )
    db.add(conn)
    db.flush()
    assert conn.id is not None
    assert conn.serves == ["fundamentals", "news"]
