"""10 以内算数题插件 Manifest。"""

from __future__ import annotations

from app.worker.plugins.manifest import Manifest

MANIFEST = Manifest(
    key="math10",
    display_name="随机算数题",
    version="1.0.0",
    author="builtin",
    description="由交互 Bot 开启一局 10 以内算数题，群内第一个答对者获得奖金",
    category="interactive",
    interaction_entries=[
        {
            "key": "start_math_game",
            "title": "随机算数题",
            "description": "转账命中或模块关键词触发后，由交互 Bot 开启一局随机算数题。",
            "session_scope": "chat",
            "events": ["payment_confirmed", "keyword", "message", "session_close"],
            "input_schema": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "prize": {
                        "type": "integer",
                        "title": "奖金",
                        "default": 123,
                        "minimum": 1,
                    },
                    "valid_seconds": {
                        "type": "integer",
                        "title": "平台会话有效期（秒）",
                        "default": 900,
                        "minimum": 30,
                        "maximum": 86400,
                    },
                },
                "required": ["prize"],
            },
        }
    ],
    permissions=["send_message"],
    config_schema={
        "type": "object",
        "x-ui-mode": "single",
        "additionalProperties": False,
        "properties": {},
    },
)

__all__ = ["MANIFEST"]
