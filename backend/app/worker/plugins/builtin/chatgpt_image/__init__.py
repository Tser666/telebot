"""ChatGPT 图片助手内置插件。"""

from .manifest import MANIFEST
from .plugin import ChatGPTImagePlugin

PLUGIN_CLASS = ChatGPTImagePlugin

__all__ = ["PLUGIN_CLASS", "MANIFEST"]
