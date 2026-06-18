from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.account_bots import list_account_bot_interaction_results
from app.api.logs import list_audit_logs
from app.db.models.log import RuntimeLog


@pytest.mark.asyncio
async def test_list_audit_logs_applies_action_filter() -> None:
    fake_db = AsyncMock()
    fake_result = MagicMock()
    fake_result.scalars.return_value.all = MagicMock(return_value=[])
    fake_db.execute = AsyncMock(return_value=fake_result)

    await list_audit_logs(
        db=fake_db,
        _user=None,  # type: ignore[arg-type]
        action="account_bot.test",
        limit=20,
    )

    stmt = fake_db.execute.await_args.args[0]
    sql = str(stmt)
    assert "audit_log.action" in sql
    assert "LIMIT" in sql


@pytest.mark.asyncio
async def test_list_audit_logs_applies_keyword_filter() -> None:
    fake_db = AsyncMock()
    fake_result = MagicMock()
    fake_result.scalars.return_value.all = MagicMock(return_value=[])
    fake_db.execute = AsyncMock(return_value=fake_result)

    await list_audit_logs(
        db=fake_db,
        _user=None,  # type: ignore[arg-type]
        keyword="restart",
        limit=20,
    )

    stmt = fake_db.execute.await_args.args[0]
    sql = str(stmt)
    assert "audit_log.action" in sql
    assert "audit_log.target" in sql


@pytest.mark.asyncio
async def test_list_account_bot_interaction_results_extracts_structured_winner() -> None:
    fake_db = AsyncMock()
    row = RuntimeLog(
        account_id=1,
        ts=datetime.now(UTC),
        level="info",
        source="event",
        message="interaction result reported",
        detail={
            "chat_id": -100123,
            "message_id": 88,
            "rule_id": "game24-paid",
            "rule_name": "24点门票",
            "plugin_key": "game24",
            "entry_key": "start_paid_game",
            "session_key": "session-1",
            "session_scope": "chat",
            "result": {
                "action_type": "result",
                "send_via": "interaction_bot",
                "execution": "bot",
                "status": "winner",
                "winner_user_id": 123,
                "winner_name": "AAA",
                "winner_message_id": 456,
                "amount": 1000,
                "payout_mode": "auto",
                "payout_account_label": "@owner",
                "settlement": {
                    "mode": "auto",
                    "amount": 1000,
                    "winner_user_id": 123,
                    "winner_name": "AAA",
                    "payout_account_label": "@owner",
                    "status": "announced",
                },
            },
        },
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all = MagicMock(return_value=[row])
    fake_db.execute = AsyncMock(return_value=fake_result)

    items = await list_account_bot_interaction_results(
        aid=1,
        db=fake_db,
        _user=None,  # type: ignore[arg-type]
        limit=20,
    )

    assert len(items) == 1
    assert items[0].chat_id == -100123
    assert items[0].message_id == 88
    assert items[0].plugin_key == "game24"
    assert items[0].winner_user_id == 123
    assert items[0].winner_name == "AAA"
    assert items[0].winner_message_id == 456
    assert items[0].amount == 1000
    assert items[0].payout_account_label == "@owner"


@pytest.mark.asyncio
async def test_list_account_bot_interaction_results_tolerates_legacy_result_values() -> None:
    fake_db = AsyncMock()
    row = RuntimeLog(
        account_id=1,
        ts=datetime.now(UTC),
        level="info",
        source="event",
        message="interaction result reported",
        detail={
            "chat_id": -100321,
            "message_id": 99,
            "rule_id": "legacy-paid",
            "rule_name": "旧插件",
            "plugin_key": "legacy_game",
            "entry_key": "start",
            "session_scope": "room",
            "result": {
                "action_type": "result",
                "send_via": "legacy_bot",
                "execution": "legacy",
                "status": "done",
                "winner_user_id": 789,
                "winner_name": "BBB",
                "amount": 88,
                "settlement": {
                    "mode": "legacy_auto",
                    "amount": 88,
                    "winner_user_id": 789,
                    "winner_name": "BBB",
                    "status": "paid_by_script",
                },
            },
        },
    )
    fake_result = MagicMock()
    fake_result.scalars.return_value.all = MagicMock(return_value=[row])
    fake_db.execute = AsyncMock(return_value=fake_result)

    items = await list_account_bot_interaction_results(
        aid=1,
        db=fake_db,
        _user=None,  # type: ignore[arg-type]
        limit=20,
    )

    assert len(items) == 1
    assert items[0].session_scope == "room"
    assert items[0].send_via == "legacy_bot"
    assert items[0].settlement is not None
    assert items[0].settlement.mode == "legacy_auto"
    assert items[0].settlement.status == "paid_by_script"
