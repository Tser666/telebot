"""24 点插件的消息形态兼容性测试。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.worker.plugins.base import PluginContext
from app.worker.plugins.builtin.game24.manifest import MANIFEST
from app.worker.plugins.builtin.game24.plugin import Game24Plugin, GameState, check_answer


def test_game24_accepts_common_answer_formats() -> None:
    assert check_answer("答案：(1＋2＋3)×4=24", [1, 2, 3, 4])
    assert check_answer("（8－4）×（3＋3）=24", [8, 4, 3, 3])


def test_game24_manifest_schema_matches_runtime_config() -> None:
    """manifest 不能再暴露旧字段 time_limit/prize/max_players。"""

    schema = MANIFEST.config_schema
    assert schema["x-ui-mode"] == "single"
    assert set(schema["properties"].keys()) == {"command", "timeout"}
    assert schema["properties"]["command"]["default"] == "24d"
    assert schema["properties"]["timeout"]["default"] == 500


@pytest.mark.asyncio
async def test_game24_accepts_bare_message_without_outgoing() -> None:
    """回归：某些 incoming 对象没有 outgoing 属性，正确答案仍应被处理。"""

    plugin = Game24Plugin()
    plugin._games[100] = GameState(
        chat_id=100,
        trigger_msg_id=10,
        numbers=[1, 2, 3, 4],
        prize=200,
        timeout=500,
    )

    async def _broken_get_sender():
        raise AttributeError("'Message' object has no attribute 'outgoing'")

    event = SimpleNamespace(
        chat_id=100,
        raw_text="(1+2+3)*4",
        sender_id=42,
        id=99,
        get_sender=_broken_get_sender,
        reply=AsyncMock(),
    )
    client = AsyncMock()
    client.get_messages.return_value = SimpleNamespace(text="原题")
    ctx = PluginContext(
        account_id=1,
        feature_key="game24",
        client=client,
        log=AsyncMock(),
    )

    await plugin.on_message(ctx, event)

    event.reply.assert_awaited_once_with("+200")
    client.send_message.assert_not_awaited()
    client.edit_message.assert_awaited_once()
    assert plugin._games[100].active is False
    assert plugin._games[100].winner_id == 42


@pytest.mark.asyncio
async def test_game24_prize_falls_back_to_client_send_message() -> None:
    """event.reply 不可用/失败时，仍应通过 client.send_message 回复奖励。"""

    plugin = Game24Plugin()
    plugin._games[100] = GameState(
        chat_id=100,
        trigger_msg_id=10,
        numbers=[1, 2, 3, 4],
        prize=200,
        timeout=500,
    )
    event = SimpleNamespace(
        chat_id=100,
        raw_text="(1+2+3)*4",
        sender_id=42,
        id=99,
        get_sender=AsyncMock(return_value=SimpleNamespace(first_name="alice", id=42)),
        reply=AsyncMock(side_effect=RuntimeError("reply blocked")),
    )
    client = AsyncMock()
    client.get_messages.return_value = SimpleNamespace(text="原题")
    ctx = PluginContext(
        account_id=1,
        feature_key="game24",
        client=client,
        log=AsyncMock(),
    )

    await plugin.on_message(ctx, event)

    event.reply.assert_awaited_once_with("+200")
    client.send_message.assert_awaited_once_with(
        entity=100,
        message="+200",
        reply_to=99,
    )
    client.edit_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_game24_announce_when_prize_send_failed() -> None:
    """发奖完全失败时，题目消息不能谎称已发放。"""

    plugin = Game24Plugin()
    plugin._games[100] = GameState(
        chat_id=100,
        trigger_msg_id=10,
        numbers=[1, 2, 3, 4],
        prize=200,
        timeout=500,
    )
    event = SimpleNamespace(
        chat_id=100,
        raw_text="(1+2+3)*4",
        sender_id=42,
        id=99,
        get_sender=AsyncMock(return_value=SimpleNamespace(first_name="alice", id=42)),
        reply=AsyncMock(side_effect=RuntimeError("reply blocked")),
    )
    client = AsyncMock()
    client.send_message.side_effect = RuntimeError("send blocked")
    client.get_messages.return_value = SimpleNamespace(text="原题")
    ctx = PluginContext(
        account_id=1,
        feature_key="game24",
        client=client,
        log=AsyncMock(),
    )

    await plugin.on_message(ctx, event)

    text = client.edit_message.call_args.kwargs["text"]
    assert "奖励消息发送失败" in text
    assert "已发放" not in text


@pytest.mark.asyncio
async def test_game24_prize_falls_back_to_plain_message_when_reply_to_fails() -> None:
    """频道/匿名消息 reply_to 失败时，至少要把 +奖金普通消息发出去。"""

    plugin = Game24Plugin()
    plugin._games[100] = GameState(
        chat_id=100,
        trigger_msg_id=10,
        numbers=[10, 9, 12, 4],
        prize=2000,
        timeout=500,
    )
    event = SimpleNamespace(
        chat_id=100,
        raw_text="12*10/(9-4)",
        sender_id=None,
        id=99,
        get_sender=AsyncMock(return_value=None),
        reply=AsyncMock(side_effect=RuntimeError("reply blocked")),
    )
    client = AsyncMock()

    async def _send_message(**kwargs):
        if "reply_to" in kwargs:
            raise RuntimeError("reply_to blocked")
        return SimpleNamespace(id=101)

    client.send_message.side_effect = _send_message
    client.get_messages.return_value = SimpleNamespace(text="原题")
    ctx = PluginContext(
        account_id=1,
        feature_key="game24",
        client=client,
        log=AsyncMock(),
    )

    await plugin.on_message(ctx, event)

    assert client.send_message.await_count == 2
    assert client.send_message.await_args_list[0].kwargs == {
        "entity": 100,
        "message": "+2000",
        "reply_to": 99,
    }
    assert client.send_message.await_args_list[1].kwargs == {
        "entity": 100,
        "message": "+2000",
    }
    text = client.edit_message.call_args.kwargs["text"]
    assert "已发放" in text
