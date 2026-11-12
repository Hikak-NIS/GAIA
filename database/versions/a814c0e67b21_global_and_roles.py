"""GAIA Global, nicknames and explicit administrative roles.

Only the already-existing designated account is promoted. Public registration never bootstraps a superadmin.
"""

from alembic import op
import sqlalchemy as sa

revision = "a814c0e67b21"
down_revision = "7b94d6120344"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("nickname", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("nickname_key", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("role", sa.String(20), nullable=False, server_default="user"))
    # Existing UUIDs provide collision-free deterministic aliases; users can subsequently choose a nickname.
    op.execute("UPDATE users SET nickname = replace(id, '-', '')")
    op.execute(
        "UPDATE users SET nickname = 'SENQwir', role = 'superadmin' WHERE lower(email) = 'gulnarapulatova9@gmail.com'"
    )
    op.execute("UPDATE users SET nickname_key = lower(nickname)")
    with op.batch_alter_table("users") as batch:
        batch.alter_column("nickname", existing_type=sa.String(32), nullable=False)
        batch.alter_column("nickname_key", existing_type=sa.String(32), nullable=False)
        batch.create_unique_constraint("uq_users_nickname_key", ["nickname_key"])
        batch.create_check_constraint("ck_users_role", "role IN ('user', 'admin', 'superadmin')")
    op.create_index(
        "uq_single_superadmin",
        "users",
        ["role"],
        unique=True,
        sqlite_where=sa.text("role = 'superadmin'"),
        postgresql_where=sa.text("role = 'superadmin'"),
    )
    op.create_table(
        "global_analyses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_global_analyses_creator_id", "global_analyses", ["creator_id"])
    op.create_table(
        "global_markers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_global_markers_creator_id", "global_markers", ["creator_id"])
    op.create_table(
        "global_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "admin_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("target_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_admin_audit_actor_id", "admin_audit", ["actor_id"])


def downgrade():
    raise RuntimeError(
        "Restore a verified pre-upgrade backup; automatic downgrade would discard administrative history"
    )
