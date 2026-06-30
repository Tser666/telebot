from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import plugin_config_actions
from app.services.plugin_config_actions import declared_config_actions, run_plugin_config_action
from app.worker.plugins.base import Plugin, PluginContext


class DemoConfigActionPlugin(Plugin):
    key = "demo_action"
    display_name = "Demo Action"

    async def on_config_action(
        self,
        ctx: PluginContext,
        action_key: str,
        payload: dict,
    ) -> dict:
        assert action_key == "make_item"
        assert ctx.config["count"] == 3
        assert ctx.config["api_token"] == "real-token"
        return {
            "message": "已生成",
            "config_patch": {
                "items": [
                    {
                        "enabled": True,
                        "name": payload["input"]["name"],
                        "count": ctx.config["count"],
                    }
                ]
            },
        }


class FakeDB:
    async def get(self, *_args, **_kwargs):
        return None


def test_declared_config_actions_reads_schema_metadata() -> None:
    feature = SimpleNamespace(
        manifest={
            "config_schema": {
                "x-config-actions": [
                    {"key": "make_item", "title": "生成"},
                    {"title": "缺少 key"},
                ]
            }
        }
    )

    actions = declared_config_actions(feature)

    assert actions == [{"key": "make_item", "title": "生成"}]


@pytest.mark.asyncio
async def test_run_plugin_config_action_merges_form_config_and_returns_patch(monkeypatch) -> None:
    feature = SimpleNamespace(
        key="demo_action",
        manifest={
            "permissions": [],
            "config_actions": [{"key": "make_item", "title": "生成"}],
        },
    )
    account = SimpleNamespace(id=7, proxy_id=None)
    monkeypatch.setattr(plugin_config_actions, "get_plugin", lambda key: DemoConfigActionPlugin)

    result = await run_plugin_config_action(
        FakeDB(),
        account=account,
        feature=feature,
        action_key="make_item",
        effective_config={"count": 1, "api_token": "real-token"},
        current_config={"count": 3, "api_token": "••••••••••••••••"},
        action_input={"name": "第一组"},
    )

    assert result["message"] == "已生成"
    assert result["config_patch"]["items"] == [
        {"enabled": True, "name": "第一组", "count": 3}
    ]
