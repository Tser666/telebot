"""插件子包入口。

保持轻量：导入 ``app.worker.plugins.manifest`` 时不应顺手加载 Telethon / 插件基类。
需要旧式便捷导出时，通过 ``__getattr__`` 懒加载 ``base``。
"""

__all__ = ["Plugin", "PluginContext", "all_plugins", "get_plugin", "register"]


def __getattr__(name: str):
    if name in __all__:
        from . import base

        return getattr(base, name)
    raise AttributeError(name)
