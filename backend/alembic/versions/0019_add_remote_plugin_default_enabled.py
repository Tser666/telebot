"""新增 remote_plugin.default_enabled 字段。

Revision ID: 0019
Revises: 0018
Create Date: 2026-05-08

远程插件安装时可指定 default_enabled=True，安装后自动为所有已有账号
创建 AccountFeature 行（复用现有 feature 矩阵体系）。
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "remote_plugin",
        sa.Column(
            "default_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("remote_plugin", "default_enabled")
