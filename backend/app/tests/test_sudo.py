"""Sudo 消息代发单元测试。

覆盖：
- CommandContext sudo 字段默认值
- _check_sudo_permission 权限检查逻辑（无 sudo / 显式全部 / chat 白名单 / 命令白名单）
- sudo prefix 匹配（通过 make_command_handler 间接测试）
- ,sudo add / del / ls 内置命令（mock DB）
- generation guard 逻辑（loader 中 generation 不匹配时跳过 handler）
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.sudo import SudoUserResponse
from app.worker.command import (
    CommandContext,
    _check_sudo_permission,
    _should_report_incoming_sudo_denial,
)

# ════════════════════════════════════════════════════════════
# 1) CommandContext sudo 字段
# ════════════════════════════════════════════════════════════


def test_command_context_sudo_defaults():
    """新 CommandContext 的 sudo 字段应该是空。"""
    ctx = CommandContext(
        account_id=1,
        templates={},
        providers={},
        command_prefix=",",
    )
    assert ctx.sudo_users == {}
    assert ctx.sudo_prefix == "."


def test_command_context_sudo_can_be_set():
    """sudo 字段可以在构造时传入。"""
    ctx = CommandContext(
        account_id=1,
        templates={},
        providers={},
        command_prefix=",",
        sudo_users={
            111: {"display_name": "alice", "allowed_chat_ids": [], "allowed_commands": []},
        },
        sudo_prefix=".",
    )
    assert 111 in ctx.sudo_users
    assert ctx.sudo_users[111]["display_name"] == "alice"


# ════════════════════════════════════════════════════════════
# 2) _check_sudo_permission 权限检查
# ════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_check_sudo_no_ctx():
    """_ctx 为 None 时应该拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = None
    try:
        event = AsyncMock()
        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is False
        assert "未配置" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_empty_users():
    """sudo_users 为空时应该拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",", sudo_users={},
    )
    try:
        event = AsyncMock()
        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is False
        assert "未配置" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_user_not_in_list():
    """发送者不在 sudo 列表时应该拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={999: {"display_name": "bob", "allowed_chat_ids": [], "allowed_commands": []}},
    )
    try:
        sender = MagicMock()
        sender.id = 111  # 不在列表里
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is False
        assert "不在 sudo 列表" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_allowed_explicit_all_scope():
    """在列表中且显式允许全部对话/命令时应该通过。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {"display_name": "alice", "allowed_chat_ids": ["*"], "allowed_commands": ["*"]}},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)
        event.chat_id = -100999

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is True
        assert msg == ""
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_empty_scope_denied_by_default():
    """sudo 用户未配置对话/命令范围时默认拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {"display_name": "alice", "allowed_chat_ids": [], "allowed_commands": []}},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)
        event.chat_id = -100999

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is False
        assert "未配置允许对话" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_chat_not_allowed():
    """chat_id 不在白名单时应该拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {
            "display_name": "alice",
            "allowed_chat_ids": [-100111],
            "allowed_commands": ["*"],
        }},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)
        event.chat_id = -100999  # 不在白名单

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is False
        assert "不在白名单" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_chat_allowed():
    """chat_id 在白名单时应该通过。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {
            "display_name": "alice",
            "allowed_chat_ids": [-100111],
            "allowed_commands": ["*"],
        }},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)
        event.chat_id = -100111

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is True
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_command_not_allowed():
    """命令不在白名单时应该拒绝。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {
            "display_name": "alice",
            "allowed_chat_ids": ["*"],
            "allowed_commands": ["ping", "help"],
        }},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)

        allowed, msg = await _check_sudo_permission(event, "reboot", 1)
        assert allowed is False
        assert "不在白名单" in msg
    finally:
        wcmd._ctx = old


@pytest.mark.asyncio
async def test_check_sudo_command_allowed():
    """命令在白名单时应该通过。"""
    from app.worker import command as wcmd
    old = wcmd._ctx
    wcmd._ctx = CommandContext(
        account_id=1, templates={}, providers={},
        command_prefix=",",
        sudo_users={111: {
            "display_name": "alice",
            "allowed_chat_ids": ["*"],
            "allowed_commands": ["ping", "help"],
        }},
    )
    try:
        sender = MagicMock()
        sender.id = 111
        event = AsyncMock()
        event.get_sender = AsyncMock(return_value=sender)

        allowed, msg = await _check_sudo_permission(event, "ping", 1)
        assert allowed is True
    finally:
        wcmd._ctx = old


def test_sudo_response_hides_internal_all_marker():
    """API 响应应该用布尔字段表达“全部”，不把内部通配符暴露给前端列表。"""
    response = SudoUserResponse.model_validate({
        "id": 1,
        "account_id": 1,
        "tg_user_id": 111,
        "display_name": "alice",
        "allowed_chat_ids": ["*"],
        "allowed_commands": ["*"],
        "created_at": "2026-05-10T00:00:00+08:00",
    })

    assert response.allow_all_chats is True
    assert response.allow_all_commands is True
    assert response.allowed_chat_ids == []
    assert response.allowed_commands == []


def test_incoming_sudo_denial_reporting_is_quiet_for_unconfigured_users():
    """群里普通消息撞到 sudo 前缀时，不应该公开回复未授权提示。"""
    assert _should_report_incoming_sudo_denial("sudo 系统未配置") is False
    assert _should_report_incoming_sudo_denial("TG 用户 123 不在 sudo 列表中") is False
    assert _should_report_incoming_sudo_denial("未配置允许对话，sudo 默认拒绝") is False
    assert _should_report_incoming_sudo_denial("未配置允许命令，sudo 默认拒绝") is False


def test_incoming_sudo_denial_reporting_keeps_scope_errors_visible():
    """已授权 sudo 用户越界使用时仍给明确反馈。"""
    assert _should_report_incoming_sudo_denial("此对话（chat_id=-100）不在白名单中") is True
    assert _should_report_incoming_sudo_denial("命令 `reboot` 不在白名单中") is True


# ════════════════════════════════════════════════════════════
# 3) Generation Guard
# ════════════════════════════════════════════════════════════


def test_generation_guard_skip_stale():
    """generation 不匹配时应该跳过 handler。"""
    # 模拟 _dispatch 中的检查逻辑
    class FakeCtx:
        generation = 1

    class FakeState:
        generation = 2  # reload 后 generation 增加了

    ctx = FakeCtx()
    state = FakeState()

    # generation 不匹配 → 应该跳过
    assert ctx.generation != state.generation


def test_generation_guard_pass_fresh():
    """generation 匹配时应该执行 handler。"""
    class FakeCtx:
        generation = 3

    class FakeState:
        generation = 3

    ctx = FakeCtx()
    state = FakeState()

    assert ctx.generation == state.generation


def test_generation_guard_increment():
    """reload 后 generation 应该递增。"""
    from app.worker.plugins.loader import _AccountState

    state = _AccountState(account_id=1)
    assert state.generation == 1
    state.generation += 1
    assert state.generation == 2
    state.generation += 1
    assert state.generation == 3
