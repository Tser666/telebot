"""Sudo 用户管理 Schemas。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from ..util.sudo_permissions import (
    normalize_sudo_chat_ids,
    normalize_sudo_commands,
    sudo_scope_all,
)


class SudoUserCreate(BaseModel):
    """创建 Sudo 用户请求。"""
    account_id: int
    tg_user_id: int
    display_name: str | None = None
    allowed_chat_ids: list[int] | None = None
    allowed_commands: list[str] | None = None
    allow_all_chats: bool = False
    allow_all_commands: bool = False


class SudoUserUpdate(BaseModel):
    """更新 Sudo 用户请求。"""
    display_name: str | None = None
    allowed_chat_ids: list[int] | None = None
    allowed_commands: list[str] | None = None
    allow_all_chats: bool | None = None
    allow_all_commands: bool | None = None


class SudoUserResponse(BaseModel):
    """Sudo 用户响应。"""
    id: int
    account_id: int
    tg_user_id: int
    display_name: str | None = None
    allowed_chat_ids: list[int] | None = None
    allowed_commands: list[str] | None = None
    allow_all_chats: bool = False
    allow_all_commands: bool = False
    created_at: str

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def normalize_scope(cls, value: Any) -> Any:
        """隐藏 DB 内部通配符，同时返回显式全部开关。"""
        if isinstance(value, dict):
            data = dict(value)
        else:
            data = {
                "id": value.id,
                "account_id": value.account_id,
                "tg_user_id": value.tg_user_id,
                "display_name": value.display_name,
                "allowed_chat_ids": getattr(value, "allowed_chat_ids", None),
                "allowed_commands": getattr(value, "allowed_commands", None),
                "created_at": value.created_at,
            }

        raw_chat_ids = data.get("allowed_chat_ids")
        raw_commands = data.get("allowed_commands")
        data["allow_all_chats"] = sudo_scope_all(raw_chat_ids)
        data["allow_all_commands"] = sudo_scope_all(raw_commands)
        data["allowed_chat_ids"] = normalize_sudo_chat_ids(raw_chat_ids)
        data["allowed_commands"] = normalize_sudo_commands(raw_commands)

        created_at = data.get("created_at")
        if created_at is not None and not isinstance(created_at, str):
            data["created_at"] = created_at.isoformat()
        return data
