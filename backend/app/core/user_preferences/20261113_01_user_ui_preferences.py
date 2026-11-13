# backend/alembic/versions/20261113_01_user_ui_preferences.py
"""user_ui_preferences

Revision ID: 20261113_01
Revises:
Create Date: 2026-11-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20261113_01"
down_revision: str | None = None  # указать текущий head проекта
create_date: str = "2026-11-13"


def upgrade() -> None:
    op.create_table(
        "user_ui_preferences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "preferences",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["public.users.id"],
            name="fk_user_ui_preferences_user_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_user_ui_preferences"),
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("user_ui_preferences", schema="public")