"""24 点游戏插件 Manifest。

Config Schema 说明：
- level: "global" 的字段为全局配置，所有账号共享
- 无 level 或 level: "account" 的字段为账号级配置
- 配置合并顺序：schema defaults < global config < account config
"""
from __future__ import annotations

from app.worker.plugins.manifest import Manifest

MANIFEST = Manifest(
    key="game24",
    display_name="24点游戏",
    version="1.0.0",
    author="builtin",
    description="随机生成 24 点题目，群内竞速答题，第一名获得奖金",
    permissions=["send_message", "edit_message", "read_chat", "delete_message"],
    # level 字段说明：
    #   - "global": 全局配置，所有账号共享
    #   - "account": 账号级配置，按账号隔离（默认）
    config_schema={
        "type": "object",
        "x-ui-mode": "single",
        "properties": {
            "time_limit": {
                "type": "integer", "title": "答题时间（秒）", "default": 30,
                "minimum": 10, "maximum": 300,
                "level": "global",
            },
            "prize": {
                "type": "integer", "title": "奖金金额", "default": 100,
                "minimum": 0,
                "level": "global",
            },
            "max_players": {
                "type": "integer", "title": "最大参与人数", "default": 50,
                "minimum": 2, "maximum": 200,
                "level": "global",
            },
        },
    },
)

__all__ = ["MANIFEST"]
