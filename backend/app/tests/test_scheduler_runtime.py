from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.worker.scheduler_runtime import PlatformScheduler


async def _noop_log(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
    return None


def _runtime() -> PlatformScheduler:
    paused = asyncio.Event()
    paused.set()
    return PlatformScheduler(
        account_id=42,
        client=AsyncMock(),
        redis=AsyncMock(),
        paused=paused,
        log_writer=_noop_log,
    )


@pytest.mark.asyncio
async def test_plugin_facade_registers_interval_job(monkeypatch) -> None:
    monkeypatch.setattr("app.worker.scheduler_runtime._get_system_tz", AsyncMock(return_value=None))

    runtime = _runtime()
    callback = AsyncMock()

    facade = runtime.for_plugin("demo", generation=1)
    facade.register("heartbeat", {"kind": "interval", "interval_sec": 60}, callback)

    await runtime.tick_runtime_jobs()

    callback.assert_awaited_once()
    job = callback.await_args.args[0]
    assert job.account_id == 42
    assert job.owner == "demo"
    assert job.job_id == "heartbeat"
    assert job.fire_count == 1

    jobs = facade.list_jobs()
    assert jobs[0]["fire_count"] == 1
    assert jobs[0]["config"]["last_result"] == "ok"
    assert jobs[0]["config"]["next_fire"] is not None


@pytest.mark.asyncio
async def test_unregister_owner_prevents_runtime_job(monkeypatch) -> None:
    monkeypatch.setattr("app.worker.scheduler_runtime._get_system_tz", AsyncMock(return_value=None))

    runtime = _runtime()
    callback = AsyncMock()
    facade = runtime.for_plugin("demo", generation=1)
    facade.register(
        "once",
        {
            "kind": "once",
            "fire_at": (datetime.now(UTC) - timedelta(seconds=1)).isoformat(),
        },
        callback,
    )

    removed = facade.unregister_all()
    await runtime.tick_runtime_jobs()

    assert removed == 1
    callback.assert_not_awaited()
    assert facade.list_jobs() == []


@pytest.mark.asyncio
async def test_runtime_job_failure_is_logged_and_kept(monkeypatch) -> None:
    monkeypatch.setattr("app.worker.scheduler_runtime._get_system_tz", AsyncMock(return_value=None))
    logs: list[tuple[tuple, dict]] = []

    async def _log(*args, **kwargs) -> None:  # noqa: ANN002, ANN003
        logs.append((args, kwargs))

    paused = asyncio.Event()
    paused.set()
    runtime = PlatformScheduler(
        account_id=42,
        client=AsyncMock(),
        redis=AsyncMock(),
        paused=paused,
        log_writer=_log,
    )

    async def _boom(_job) -> None:  # noqa: ANN001
        raise RuntimeError("boom")

    runtime.for_plugin("demo", generation=1).register(
        "broken",
        {"kind": "interval", "interval_sec": 60},
        _boom,
    )

    await runtime.tick_runtime_jobs()

    jobs = runtime.list_runtime_jobs()
    assert jobs[0]["fire_count"] == 0
    assert jobs[0]["last_error"] == "RuntimeError: boom"
    assert jobs[0]["config"]["last_result"] == "error"
    assert logs
    assert logs[0][1]["source"] == "plugin"
    assert logs[0][1]["plugin_key"] == "demo"
