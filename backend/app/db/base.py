"""SQLAlchemy 异步引擎与基类。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from ..settings import settings


class Base(DeclarativeBase):
    """所有模型继承此基类。"""


def _engine_kwargs() -> dict:
    """按数据库类型构造连接池参数；小 VPS 默认保持紧凑。"""

    kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }
    if settings.database_url.startswith("postgresql"):
        kwargs.update(
            {
                "pool_size": max(1, int(settings.db_pool_size or 1)),
                "max_overflow": max(0, int(settings.db_max_overflow or 0)),
                "pool_timeout": max(1, int(settings.db_pool_timeout or 30)),
            }
        )
    return kwargs


# 全局异步引擎与 session factory
engine = create_async_engine(settings.database_url, **_engine_kwargs())

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)
