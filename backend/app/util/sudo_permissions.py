"""Sudo 权限作用域工具。

历史上 sudo 的空白名单表示“全部允许”。现在改为默认零权限：
- ``[]`` / ``None``：不允许任何对话或命令
- ``["*"]``：显式允许全部
- 其他列表：只允许列表内的对话或命令
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

SUDO_ALL_MARKER = "*"


def _iter_scope(values: Iterable[Any] | None) -> list[Any]:
    if values is None:
        return []
    return list(values)


def _is_all_marker(value: Any) -> bool:
    return str(value).strip() == SUDO_ALL_MARKER


def sudo_scope_all(values: Iterable[Any] | None) -> bool:
    """作用域是否显式允许全部。"""
    return any(_is_all_marker(value) for value in _iter_scope(values))


def normalize_sudo_chat_ids(values: Iterable[Any] | None) -> list[int]:
    """移除通配标记并规整 chat_id 白名单。"""
    result: list[int] = []
    seen: set[int] = set()
    for value in _iter_scope(values):
        if _is_all_marker(value):
            continue
        try:
            chat_id = int(value)
        except (TypeError, ValueError):
            continue
        if chat_id not in seen:
            seen.add(chat_id)
            result.append(chat_id)
    return result


def normalize_sudo_commands(values: Iterable[Any] | None) -> list[str]:
    """移除通配标记并规整命令白名单。"""
    result: list[str] = []
    seen: set[str] = set()
    for value in _iter_scope(values):
        if _is_all_marker(value):
            continue
        command = str(value).strip()
        if not command:
            continue
        if command not in seen:
            seen.add(command)
            result.append(command)
    return result


def build_sudo_chat_scope(
    allowed_chat_ids: Iterable[Any] | None,
    *,
    allow_all: bool = False,
) -> list[int | str]:
    """构造存储到 DB 的 sudo 对话作用域。"""
    if allow_all:
        return [SUDO_ALL_MARKER]
    return normalize_sudo_chat_ids(allowed_chat_ids)


def build_sudo_command_scope(
    allowed_commands: Iterable[Any] | None,
    *,
    allow_all: bool = False,
) -> list[str]:
    """构造存储到 DB 的 sudo 命令作用域。"""
    if allow_all:
        return [SUDO_ALL_MARKER]
    return normalize_sudo_commands(allowed_commands)


def sudo_chat_allowed(values: Iterable[Any] | None, chat_id: Any) -> bool:
    """检查 chat_id 是否被 sudo 对话作用域允许。"""
    if sudo_scope_all(values):
        return True
    allowed = normalize_sudo_chat_ids(values)
    if not allowed:
        return False
    try:
        current_chat_id = int(chat_id)
    except (TypeError, ValueError):
        return False
    return current_chat_id in set(allowed)


def sudo_command_allowed(values: Iterable[Any] | None, command: str) -> bool:
    """检查命令是否被 sudo 命令作用域允许。"""
    if sudo_scope_all(values):
        return True
    allowed = normalize_sudo_commands(values)
    if not allowed:
        return False
    return command in set(allowed)


def describe_sudo_scope(values: Iterable[Any] | None) -> str:
    """用于命令行展示的作用域描述。"""
    if sudo_scope_all(values):
        return "全部（显式）"
    normalized = normalize_sudo_commands(values)
    if not normalized:
        normalized_chat_ids = normalize_sudo_chat_ids(values)
        if normalized_chat_ids:
            return ",".join(str(item) for item in normalized_chat_ids)
        return "未授权"
    return ",".join(normalized)
