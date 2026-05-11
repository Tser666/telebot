"""内置插件：定时任务兼容入口。

scheduler 已经迁移为 worker 级平台基础能力。这个文件只保留插件注册壳，
让历史 manifest、测试、前端配置入口和远程引用不需要一次性改名。
"""

from __future__ import annotations

from app.db.models.feature import FEATURE_SCHEDULER
from app.worker.plugins.base import Plugin, PluginContext, register
from app.worker.scheduler_runtime import (
    SchedulerRuleExecutor,
    _croniter_next,
    _croniter_prev,
    _get_system_tz,
    _parse_dt,
    _to_iso,
    _to_positive_int,
)


@register
class SchedulerPlugin(SchedulerRuleExecutor, Plugin):
    """定时任务兼容壳。

    真正的 tick loop 和插件注册任务由 ``PlatformScheduler`` 负责；本类仅保留旧
    ``SchedulerPlugin`` 的方法表，便于历史测试、手动导入和旧配置继续工作。
    """

    key = FEATURE_SCHEDULER
    display_name = "定时任务"

    async def on_startup(self, ctx: PluginContext) -> None:
        if ctx.log is not None:
            await ctx.log("info", "[scheduler] 兼容插件壳已加载；平台调度器负责实际执行")

    async def on_shutdown(self, ctx: PluginContext) -> None:
        if ctx.log is not None:
            await ctx.log("info", "[scheduler] 兼容插件壳已停止")


PLUGIN_CLASS = SchedulerPlugin


__all__ = [
    "PLUGIN_CLASS",
    "SchedulerPlugin",
    "_croniter_next",
    "_croniter_prev",
    "_get_system_tz",
    "_parse_dt",
    "_to_iso",
    "_to_positive_int",
]
