from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.features import _preserve_existing_sensitive_values, _sanitize_config
from app.api.logs import RuntimeLogItem, list_audit_logs
from app.services import audit
from app.services.redactor import redact_text, redact_value


def test_redactor_masks_text_and_nested_fields() -> None:
    src = {
        "access_token": "abc123456789",
        "proxy_url": "http://user:pass@example.com:8080",
        "nested": {"api_key": "sk-test-1234567890"},
    }
    out = redact_value(src)
    assert out["access_token"] == "***"
    assert out["nested"]["api_key"] == "***"
    assert out["proxy_url"] == "http://***:***@example.com:8080"
    assert redact_text("Bearer abcdefghijklmnop") == "Bearer ***"
    assert redact_text("socks5://user:pass@127.0.0.1:1080") == "socks5://***:***@127.0.0.1:1080"


def test_redactor_preserves_non_secret_token_counters() -> None:
    out = redact_value(
        {
            "max_tokens": 4096,
            "daily_tokens": 123,
            "token_budget": 50,
            "bot_token": "123456789:secret",
            "accessToken": "abc123456789",
        }
    )
    assert out["max_tokens"] == 4096
    assert out["daily_tokens"] == 123
    assert out["token_budget"] == 50
    assert out["bot_token"] == "***"
    assert out["accessToken"] == "***"


@pytest.mark.asyncio
async def test_audit_write_redacts_detail() -> None:
    class _FakeDB:
        def __init__(self) -> None:
            self.rows: list[object] = []

        def add(self, row: object) -> None:
            self.rows.append(row)

    db = _FakeDB()
    await audit.write(
        db, 1, "feature.config.update", detail={"token": "abcd1234", "safe": "ok"}
    )
    row = db.rows[0]
    assert row.detail["token"] == "***"
    assert row.detail["safe"] == "ok"


def test_feature_config_preserve_sensitive_values() -> None:
    merged = _preserve_existing_sensitive_values(
        {"access_token": "old", "command": "cximg"},
        {"access_token": "", "command": "new-cmd"},
    )
    assert merged["access_token"] == "old"
    assert merged["command"] == "new-cmd"
    assert _sanitize_config({"access_token": "real"})["access_token"] == "***"


def test_runtime_log_item_redacts_message_and_detail() -> None:
    row = SimpleNamespace(
        id=1,
        ts=datetime.now(UTC),
        account_id=2,
        level="info",
        source="plugin",
        message="token=abcdef123456",
        detail={"api_key": "sk-1234567890"},
    )
    item = RuntimeLogItem.from_row(row)  # type: ignore[arg-type]
    assert "abcdef123456" not in item.message
    assert item.detail["api_key"] == "***"


@pytest.mark.asyncio
async def test_list_audit_logs_redacts_response_detail() -> None:
    ts = datetime.now(UTC)
    row = SimpleNamespace(
        id=1,
        ts=ts,
        user_id=1,
        action="x",
        target="y",
        detail={"password": "secret123"},
    )

    result_proxy = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [row]),
    )
    db = SimpleNamespace(execute=AsyncMock(return_value=result_proxy))
    items = await list_audit_logs(db=db, _user=SimpleNamespace(id=1), limit=10)
    assert items[0].detail["password"] == "***"
