from __future__ import annotations

from sqlalchemy import text


def test_org_and_connections_tables_exist(db):
    # organizations seeded with a default row, every user backfilled
    org_count = db.execute(text("SELECT count(*) FROM organizations")).scalar_one()
    assert org_count >= 1

    null_orgs = db.execute(text("SELECT count(*) FROM users WHERE org_id IS NULL")).scalar_one()
    assert null_orgs == 0

    # data_connections exists and is empty
    conn_count = db.execute(text("SELECT count(*) FROM data_connections")).scalar_one()
    assert conn_count == 0
