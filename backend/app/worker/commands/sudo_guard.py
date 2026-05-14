"""Sudo incoming 命令门禁与权限检查逻辑。"""
from __future__ import annotations

from typing import Any

from ...util.sudo_permissions import (
    normalize_sudo_chat_ids,
    normalize_sudo_commands,
    sudo_chat_allowed,
    sudo_command_allowed,
    sudo_scope_all,
)


async def check_sudo_permission(ctx: Any, event: Any, cmd: str) -> tuple[bool, str]:
    """检查 sudo 权限。

    Returns:
        (allowed, error_message)
    """
    if ctx is None or not ctx.sudo_enabled:
        return False, "sudo 系统未开启"
    if not ctx.sudo_users:
        return False, "sudo 系统未配置"

    sender = await event.get_sender()
    tg_user_id = getattr(sender, "id", None)
    if tg_user_id is None:
        return False, "无法识别发送者"

    sudo_config = ctx.sudo_users.get(tg_user_id)
    if sudo_config is None:
        return False, f"TG 用户 {tg_user_id} 不在 sudo 列表中"

    allowed_chats = sudo_config.get("allowed_chat_ids", [])
    chat_id = getattr(event, "chat_id", None)
    if not sudo_chat_allowed(allowed_chats, chat_id):
        if not sudo_scope_all(allowed_chats) and not normalize_sudo_chat_ids(allowed_chats):
            return False, "未配置允许对话，sudo 默认拒绝"
        return False, f"此对话（chat_id={chat_id}）不在白名单中"

    allowed_cmds = sudo_config.get("allowed_commands", [])
    if not sudo_command_allowed(allowed_cmds, cmd):
        if not sudo_scope_all(allowed_cmds) and not normalize_sudo_commands(allowed_cmds):
            return False, "未配置允许命令，sudo 默认拒绝"
        return False, f"命令 `{cmd}` 不在白名单中"

    return True, ""


def should_report_incoming_sudo_denial(error_msg: str) -> bool:
    """incoming sudo 拒绝是否需要在群里回提示。"""
    silent_fragments = (
        "sudo 系统未开启",
        "sudo 系统未配置",
        "不在 sudo 列表中",
        "未配置允许对话",
        "未配置允许命令",
    )
    return not any(fragment in error_msg for fragment in silent_fragments)


def looks_like_command_name(cmd: str, *, prefix: str = ".") -> bool:
    """判断 sudo 前缀后的 token 是否像一个真实命令名。"""
    name = str(cmd or "").strip()
    if not name:
        return False
    if prefix and name.startswith(prefix):
        return False
    return any(ch.isalnum() or ch == "_" for ch in name)


def has_dispatch_target(
    cmd: str,
    *,
    args_raw: str = "",
    builtin_alias_to_primary: dict[str, str],
    ctx: Any,
) -> bool:
    """sudo incoming 只对真实可派发命令做权限提示。"""
    if cmd in builtin_alias_to_primary:
        return True
    if ctx is not None:
        if cmd in ctx.templates:
            return True
        if ctx.aliases:
            full_rest = f"{cmd} {args_raw}".strip() if args_raw else cmd
            for alias in ctx.aliases:
                if full_rest == alias or full_rest.startswith(alias + " "):
                    return True
    return False


def is_self_chat(event: Any, *, ctx: Any) -> bool:
    """sudo incoming 只允许在账号自身 chat（收藏夹语义）触发。"""
    if ctx is None or ctx.self_tg_user_id is None:
        return False
    try:
        chat_id = int(getattr(event, "chat_id", 0) or 0)
    except Exception:
        return False
    return chat_id == int(ctx.self_tg_user_id)
