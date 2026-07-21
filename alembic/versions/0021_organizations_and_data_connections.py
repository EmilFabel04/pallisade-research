from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021_organizations_and_data_connections"
down_revision = "0020_surveillance_books"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # Seed a single default org and backfill every existing user into it.
    op.execute("INSERT INTO organizations (name) VALUES ('Pallisade')")
    op.add_column("users", sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("UPDATE users SET org_id = (SELECT id FROM organizations LIMIT 1)")
    op.alter_column("users", "org_id", nullable=False)
    op.create_foreign_key(
        "users_org_id_fkey", "users", "organizations", ["org_id"], ["id"],
    )

    op.create_table(
        "data_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("connector_type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="disconnected"),
        sa.Column("credentials_encrypted", sa.Text(), nullable=True),
        sa.Column("config_json", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("serves", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("'{}'::text[]")),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("status in ('disconnected','connected','error')",
                           name="data_connections_status_check"),
    )
    op.create_index("ix_data_connections_org_id", "data_connections", ["org_id"])


def downgrade() -> None:
    op.drop_table("data_connections")
    op.drop_constraint("users_org_id_fkey", "users", type_="foreignkey")
    op.drop_column("users", "org_id")
    op.drop_table("organizations")
