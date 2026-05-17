from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.features import _preserve_existing_sensitive_values, _sanitize_config
from app.worker.plugins.base import PluginContext
from app.worker.plugins.builtin.chatgpt_image.client import ImageResult
from app.worker.plugins.builtin.chatgpt_image.importers import extract_auth_session_access_token
from app.worker.plugins.builtin.chatgpt_image.manifest import MANIFEST
from app.worker.plugins.builtin.chatgpt_image.plugin import (
    CONFIG_RELOAD_KEYS,
    ChatGPTImagePlugin,
    _load_config,
    _parse_image_args,
)
from app.worker.plugins.builtin.chatgpt_image.token_pool import (
    TokenEntry,
    TokenPool,
    mask_token,
    parse_token_entries,
    parse_token_lines,
    token_id,
)


def test_chatgpt_image_manifest_has_chinese_config_descriptions() -> None:
    schema = MANIFEST.config_schema or {}
    props = schema["properties"]

    assert MANIFEST.key == "chatgpt_image"
    assert schema["x-ui-mode"] == "single"
    assert props["command"]["title"] == "文生图命令"
    assert "一条一条保存" in props["tokens"]["description"]
    assert "proxy_id" not in props
    assert "proxy_url" not in props
    assert "notify_chat_id" not in props
    assert props["edit_command"]["default"] == "edit"
    assert props["admin_command"]["default"] == "gptimg"


def test_chatgpt_image_config_and_args_are_customizable() -> None:
    cfg = _load_config(
        {
            "command": "画",
            "edit_command": "改",
            "admin_command": "图管",
            "default_model": "codex-gpt-image-2",
            "default_count": 2,
            "max_count": 3,
            "available_models": "gpt-image-2\ncodex-gpt-image-2",
            "style_templates": "海报=海报风格：{prompt}",
            "tokens": [{"token": "tok-a", "note": "主号"}],
        }
    )

    parsed = _parse_image_args(["-m", "gpt-image-2", "-n", "3", "-s", "海报", "咖啡", "新品"], cfg)

    assert cfg.command == "画"
    assert cfg.edit_command == "改"
    assert cfg.admin_command == "图管"
    assert cfg.tokens == [TokenEntry(token="tok-a", note="主号")]
    assert "poll_timeout" in CONFIG_RELOAD_KEYS
    assert "timeout" in CONFIG_RELOAD_KEYS
    assert "proxy_id" not in CONFIG_RELOAD_KEYS
    assert parsed.model == "gpt-image-2"
    assert parsed.count == 3
    assert parsed.style == "海报"
    assert parsed.prompt == "咖啡 新品"


def test_token_pool_round_robin_and_failure_skip() -> None:
    pool = TokenPool()
    pool.sync([TokenEntry(token="tok-a", note="一号"), TokenEntry(token="tok-b", note="二号")])

    first = pool.choose()
    second = pool.choose()
    pool.mark_failure(first.token, "HTTP 429", skip_seconds=60)
    third = pool.choose()

    assert first.token == "tok-a"
    assert second.token == "tok-b"
    assert third.token == "tok-b"
    assert first.note == "一号"
    assert token_id("tok-a").startswith("token:")
    assert parse_token_lines("a\na,b") == ["a", "b"]


def test_structured_tokens_keep_notes_and_legacy_tokens() -> None:
    entries = parse_token_entries(
        [{"token": "tok-a", "note": "主号"}, {"token": "tok-b", "note": "sub2api"}],
        "tok-b\ntok-c",
    )

    assert entries == [
        TokenEntry(token="tok-a", note="主号"),
        TokenEntry(token="tok-b", note="sub2api"),
        TokenEntry(token="tok-c", note=""),
    ]
    assert mask_token("abcdefghijklmnopqrstuvwxyz1234567890") == "abcdefghij···1234567890"


def test_auth_session_json_extracts_access_token() -> None:
    raw = '{"user":{"email":"me@example.com"},"accessToken":"tok-from-session"}'

    assert extract_auth_session_access_token(raw) == "tok-from-session"


def test_chatgpt_image_config_sanitizes_and_preserves_tokens() -> None:
    raw_token = "abcdefghijklmnopqrstuvwxyz1234567890"
    existing = {
        "tokens": [{"token": raw_token, "note": "主号"}],
        "sub2api_api_key": "real-api-key",
        "cpa_secret_key": "real-secret-key",
    }

    sanitized = _sanitize_config(existing, "chatgpt_image")
    assert sanitized["tokens"][0]["token"] == "abcdefghij···1234567890"
    assert sanitized["tokens"][0]["token_id"].startswith("token:")
    assert sanitized["sub2api_api_key"] == "***"
    assert sanitized["cpa_secret_key"] == "***"

    incoming = {
        "tokens": [{**sanitized["tokens"][0], "note": "改名"}],
        "sub2api_api_key": "***",
        "cpa_secret_key": "***",
    }
    preserved = _preserve_existing_sensitive_values(existing, incoming, "chatgpt_image")

    assert preserved["tokens"] == [{"token": raw_token, "note": "改名"}]
    assert preserved["sub2api_api_key"] == "real-api-key"
    assert preserved["cpa_secret_key"] == "real-secret-key"


@pytest.mark.asyncio
async def test_generate_command_sends_image_result(monkeypatch) -> None:
    plugin = ChatGPTImagePlugin()
    ctx = PluginContext(
        account_id=1,
        feature_key="chatgpt_image",
        config={"tokens": [{"token": "tok-a", "note": "测试"}], "command": "draw"},
        client=SimpleNamespace(send_file=AsyncMock()),
        log=AsyncMock(),
        account_proxy_url="socks5://127.0.0.1:1080",
    )
    await plugin.on_startup(ctx)
    assert plugin._proxy_label() == "跟随账号代理"

    async def fake_run_with_token(*args, **kwargs):
        return [
            ImageResult(
                data=b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
                mime_type="image/png",
                width=1,
                height=1,
                extension=".png",
            )
        ]

    monkeypatch.setattr(plugin, "_run_with_token", fake_run_with_token)
    event = SimpleNamespace(
        chat_id=123,
        id=456,
        message=SimpleNamespace(id=456, chat_id=123),
        edit=AsyncMock(),
        respond=AsyncMock(),
    )

    await plugin._cmd_generate(ctx.client, event, ["一只", "猫"], 1, ctx)

    assert ctx.client.send_file.await_count == 1
    sent = ctx.client.send_file.await_args.args[1]
    assert sent.name.endswith(".png")
    assert event.edit.await_args_list[-1].args[0].startswith("已完成")


@pytest.mark.asyncio
async def test_token_add_updates_token_config(monkeypatch) -> None:
    plugin = ChatGPTImagePlugin()
    ctx = PluginContext(
        account_id=1,
        feature_key="chatgpt_image",
        config={"tokens": [{"token": "tok-a", "note": "旧"}]},
        client=None,
        log=AsyncMock(),
    )
    await plugin.on_startup(ctx)
    saved: dict[str, object] = {}

    async def fake_save(_ctx, updates):
        saved.update(updates)

    monkeypatch.setattr(plugin, "_save_account_config", fake_save)

    result = await plugin._token_command(ctx, ["add", "tok-b"])

    assert "已添加 1 个" in result
    assert saved["tokens"] == [
        {"token": "tok-a", "note": "旧"},
        {"token": "tok-b", "note": "Telegram 命令添加"},
    ]


@pytest.mark.asyncio
async def test_token_add_accepts_auth_session_json(monkeypatch) -> None:
    plugin = ChatGPTImagePlugin()
    ctx = PluginContext(
        account_id=1,
        feature_key="chatgpt_image",
        config={"tokens": []},
        client=None,
        log=AsyncMock(),
    )
    await plugin.on_startup(ctx)
    saved: dict[str, object] = {}

    async def fake_save(_ctx, updates):
        saved.update(updates)

    monkeypatch.setattr(plugin, "_save_account_config", fake_save)

    result = await plugin._token_command(ctx, ["add", '{"accessToken":"tok-json"}'])

    assert "已添加 1 个" in result
    assert saved["tokens"] == [{"token": "tok-json", "note": "chatgpt.com session JSON"}]
