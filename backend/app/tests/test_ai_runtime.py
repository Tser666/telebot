from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from app.services import ai_runtime as service_ai_runtime
from app.services.llm_client import LLMResult
from app.services.llm_dto import LLMProviderDTO
from app.worker import ai_runtime
from app.worker import command as wcmd
from app.worker.command import CommandContext


@pytest.fixture(autouse=True)
def _reset_ctx():
    wcmd.set_command_context(CommandContext(account_id=1, templates={}, providers={}))
    yield
    wcmd.set_command_context(CommandContext(account_id=1, templates={}, providers={}))


@pytest.mark.asyncio
async def test_run_ai_wrapper_delegates_to_ai_runtime(monkeypatch) -> None:
    client = AsyncMock()
    event = AsyncMock()
    tpl = {"name": "ai", "type": "ai", "config": {"provider_id": 1}}
    invoked = AsyncMock()
    monkeypatch.setattr(ai_runtime, "invoke", invoked)

    await wcmd._run_ai(client, event, ["hi"], tpl, account_id=7)

    invoked.assert_awaited_once_with(client, event, ["hi"], tpl, 7)


@pytest.mark.asyncio
async def test_ai_runtime_missing_provider_id_shows_error() -> None:
    client = AsyncMock()
    event = AsyncMock()

    await ai_runtime.invoke(client, event, ["hi"], {"name": "ai", "type": "ai", "config": {}}, 1)

    event.edit.assert_awaited_once()
    assert "provider_id" in event.edit.call_args.args[0]


@pytest.mark.asyncio
async def test_ai_runtime_provider_not_loaded_returns_friendly_error(monkeypatch) -> None:
    from app.worker import runtime as worker_runtime

    monkeypatch.setattr(worker_runtime, "_refresh_command_context", AsyncMock(return_value=None))
    wcmd.set_command_context(CommandContext(account_id=1, templates={}, providers={}))

    client = AsyncMock()
    event = AsyncMock()
    tpl = {"name": "ai", "type": "ai", "config": {"provider_id": 99}}

    await ai_runtime.invoke(client, event, ["q"], tpl, 1)

    event.edit.assert_awaited()
    assert "99" in event.edit.call_args.args[0]


@pytest.mark.asyncio
async def test_ai_runtime_rejects_non_vision_provider_before_download(monkeypatch) -> None:
    from app.worker import runtime as worker_runtime

    monkeypatch.setattr(worker_runtime, "_refresh_command_context", AsyncMock(return_value=None))

    replied = AsyncMock()
    replied.text = ""
    replied.message = ""
    replied.photo = object()
    replied.download_media = AsyncMock(return_value=b"bad")

    wcmd.set_command_context(
        CommandContext(
            account_id=1,
            templates={},
            providers={
                7: {
                    "id": 7,
                    "name": "text-only",
                    "provider": "openai",
                    "api_key_enc": None,
                    "base_url": None,
                    "default_model": "gpt-4o",
                    "modality": "text",
                    "tags": [],
                    "cost_tier": 1,
                    "notes": None,
                    "proxy_url": None,
                    "models": [],
                }
            },
        )
    )

    client = AsyncMock()
    event = AsyncMock()
    event.get_reply_message = AsyncMock(return_value=replied)
    event.message = AsyncMock()
    event.message.photo = None
    tpl = {"name": "ai", "type": "ai", "config": {"provider_id": 7, "routing_mode": "fixed"}}

    await ai_runtime.invoke(client, event, ["问图"], tpl, 1)

    event.edit.assert_awaited()
    assert "识图" in event.edit.call_args.args[0] or "vision" in event.edit.call_args.args[0]
    replied.download_media.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_ai_runtime_delegates_shared_fallback_logic(monkeypatch) -> None:
    primary = LLMProviderDTO(id=1, name="primary", provider="openai", default_model="gpt-4o")
    fallback = LLMProviderDTO(id=2, name="fallback", provider="openai", default_model="gpt-4o-mini")
    providers = {1: primary, 2: fallback}
    chain = object()
    result = LLMResult(text="ok", model="gpt-4o", input_tokens=1, output_tokens=2)

    build_chain = Mock(return_value=chain)
    call = AsyncMock(return_value=(result, fallback, True))
    monkeypatch.setattr(service_ai_runtime, "build_fallback_chain", build_chain)
    monkeypatch.setattr(service_ai_runtime, "call_with_fallback", call)

    got = await service_ai_runtime.invoke(
        primary,
        providers,
        "sys",
        "user",
        override_model="custom",
        max_tokens=99,
        images=[b"img"],
        account_id=7,
        source="scheduler",
        fallback_provider_id=2,
        matched_tag="scheduler",
    )

    build_chain.assert_called_once_with(
        primary,
        providers=providers,
        fallback_provider_id=2,
        matched_tag="scheduler",
    )
    call.assert_awaited_once()
    kwargs = call.await_args.kwargs
    assert kwargs["source"] == "scheduler"
    assert kwargs["account_id"] == 7
    assert kwargs["override_model"] == "custom"
    assert kwargs["max_tokens"] == 99
    assert kwargs["images"] == [b"img"]
    assert got == (result, fallback, True)


@pytest.mark.asyncio
async def test_worker_ai_runtime_uses_shared_service_invoke(monkeypatch) -> None:
    fake_result = LLMResult(text="answer", model="gpt-4o", input_tokens=3, output_tokens=4)
    invoke_mock = AsyncMock(return_value=(fake_result, LLMProviderDTO(id=1, name="primary", provider="openai", default_model="gpt-4o"), False))
    monkeypatch.setattr(service_ai_runtime, "invoke", invoke_mock)
    monkeypatch.setattr("app.worker.runtime._refresh_command_context", AsyncMock(return_value=None))

    wcmd.set_command_context(
        CommandContext(
            account_id=1,
            templates={},
            providers={
                1: {
                    "id": 1,
                    "name": "primary",
                    "provider": "openai",
                    "default_model": "gpt-4o",
                    "api_key_enc": None,
                    "modality": "text",
                    "tags": [],
                    "cost_tier": 2,
                }
            },
        )
    )

    client = AsyncMock()
    event = AsyncMock()
    event.get_reply_message = AsyncMock(return_value=None)
    event.message = AsyncMock()
    event.message.photo = None
    event.message.document = None
    event.message.voice = None
    event.message.audio = None
    tpl = {"name": "ai", "type": "ai", "config": {"provider_id": 1}}

    await ai_runtime.invoke(client, event, ["hello"], tpl, 1)

    invoke_mock.assert_awaited_once()
    provider_dto, provider_map, system, user_msg = invoke_mock.await_args.args[:4]
    assert provider_dto.id == 1
    assert provider_map[1].name == "primary"
    assert user_msg == "hello"
    assert "严格规则" in system
    event.edit.assert_awaited()
