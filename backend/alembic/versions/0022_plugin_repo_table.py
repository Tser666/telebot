"""create plugin_repo table

Revision ID: 0022
Revises: 0021
Create Date: 2026-05-11

新增表：``plugin_repo``
- 阶段 F：可浏览的 Git 仓库列表（每行 = 一个保存的仓库 URL，仓库内可含多个插件）
- ``url`` 唯一约束：同一个仓库 URL 只允许保存一次
- 与 ``remote_plugin``（单插件安装记录）解耦：``plugin_repo`` 只做“目录”，
  真正落地安装仍走 ``remote_plugin`` 路径
- 注意：0012_drop_plugin_repo.py 曾删除一张同名旧表（schema 与本表不同），
  此处的迁移与那次回退无关，命名相同纯属同一资源的语义复用
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "plugin_repo",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_plugin_repo_url",
        "plugin_repo",
        ["url"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_plugin_repo_url", table_name="plugin_repo")
    op.drop_table("plugin_repo")
