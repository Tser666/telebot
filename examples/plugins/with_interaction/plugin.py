"""with_interaction 示例模块主类。"""

from __future__ import annotations

from typing import Any

from app.worker.plugins.base import Plugin, PluginContext, register


@register
class WithInteractionPlugin(Plugin):
    key = "with_interaction"
    display_name = "交互示例"

    async def on_command(
        self,
        ctx: PluginContext,
        cmd: str,
        args: list[str],
        event: Any,
    ) -> bool:
        if cmd != "with_interaction":
            return False
        await event.reply("原命令触发仍然可用")
        return True

    async def on_interaction(
        self,
        ctx: PluginContext,
        entry_key: str,
        payload: dict[str, Any],
    ) -> list[dict[str, Any]] | None:
        if entry_key != "start_with_interaction":
            return None
        message = str(payload.get("message") or "你好，交互 Bot").strip() or "你好，交互 Bot"
        actor = payload.get("actor") if isinstance(payload.get("actor"), dict) else {}
        return [
            {
                "type": "send_message",
                "text": f"{message}\n触发人：{actor.get('display_name') or actor.get('user_id') or '未知'}",
            },
            {
                "type": "result",
                "success": True,
                "result": {
                    "status": "ok",
                    "actor_user_id": actor.get("user_id"),
                    "entry_key": entry_key,
                },
                "settlement": {
                    "mode": "announce_only",
                    "winner_user_id": actor.get("user_id"),
                    "winner_name": actor.get("display_name"),
                },
            },
            {"type": "end_session"},
        ]
