"""create account bot tables

Revision ID: 0021
Revises: 0020
Create Date: 2026-05-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_bot",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "account_id",
            sa.BigInteger(),
            sa.ForeignKey("account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bot_token_enc", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="disabled"),
        sa.Column("last_update_id", sa.BigInteger(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", name="uq_account_bot_account_id"),
    )
    op.create_index("ix_account_bot_account_id", "account_bot", ["account_id"])

    op.create_table(
        "account_bot_user",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "account_id",
            sa.BigInteger(),
            sa.ForeignKey("account.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tg_user_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="viewer"),
        sa.Column("notify_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_chat_id", sa.BigInteger(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "tg_user_id", name="uq_account_bot_user_account_tg"),
    )
    op.create_index(
        "ix_account_bot_user_account_enabled",
        "account_bot_user",
        ["account_id", "enabled"],
    )
    op.create_index(
        "ix_account_bot_user_tg_user_id",
        "account_bot_user",
        ["tg_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_account_bot_user_tg_user_id", table_name="account_bot_user")
    op.drop_index("ix_account_bot_user_account_enabled", table_name="account_bot_user")
    op.drop_table("account_bot_user")
    op.drop_index("ix_account_bot_account_id", table_name="account_bot")
    op.drop_table("account_bot")
