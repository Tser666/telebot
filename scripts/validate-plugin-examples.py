#!/usr/bin/env python3
"""Validate maintained plugin examples without network or private LLM access."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_ROOT = ROOT / "examples" / "plugins"
BACKEND_ROOT = ROOT / "backend"

for import_root in (ROOT, BACKEND_ROOT):
    path = str(import_root)
    if path not in sys.path:
        sys.path.insert(0, path)

from app.worker.plugins.base import Plugin  # noqa: E402
from app.worker.plugins.manifest import Manifest  # noqa: E402

INCLUDED_EXAMPLES = {"with_http", "with_ai", "with_interaction"}
SKIPPED_EXAMPLES = {
    "translate": "历史示例仍依赖后端私有 LLM 链路，迁移到 ctx.ai 前不纳入稳定 API gate。",
}
REQUIRED_FILES = {"plugin.json", "manifest.py", "plugin.py", "__init__.py"}
REQUIRED_PERMISSIONS = {
    "with_ai": {"ai_text"},
    "with_http": {"external_http"},
}


def _load_plugin_json(plugin_dir: Path) -> dict[str, Any]:
    path = plugin_dir / "plugin.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{path}: plugin.json 不是合法 JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise AssertionError(f"{path}: plugin.json 顶层必须是 object")
    return data


def _validate_example(name: str) -> None:
    plugin_dir = EXAMPLES_ROOT / name
    missing = sorted(file for file in REQUIRED_FILES if not (plugin_dir / file).is_file())
    if missing:
        raise AssertionError(f"{plugin_dir}: 缺少必要文件: {', '.join(missing)}")

    metadata = _load_plugin_json(plugin_dir)
    module = importlib.import_module(f"examples.plugins.{name}")

    manifest = getattr(module, "MANIFEST", None)
    plugin_cls = getattr(module, "PLUGIN_CLASS", None)
    if not isinstance(manifest, Manifest):
        raise AssertionError(f"{name}: MANIFEST 必须是 Manifest 实例")
    if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, Plugin):
        raise AssertionError(f"{name}: PLUGIN_CLASS 必须是 Plugin 子类")

    instance = plugin_cls()
    if not isinstance(instance, Plugin):
        raise AssertionError(f"{name}: PLUGIN_CLASS 无法实例化为 Plugin")

    plugin_json_key = metadata.get("name") or metadata.get("key")
    if plugin_json_key != manifest.key or plugin_cls.key != manifest.key:
        raise AssertionError(
            f"{name}: key 不一致: plugin.json={plugin_json_key!r}, "
            f"MANIFEST={manifest.key!r}, PLUGIN_CLASS={plugin_cls.key!r}"
        )
    if metadata.get("version") != manifest.version:
        raise AssertionError(f"{name}: plugin.json.version 与 MANIFEST.version 不一致")
    if metadata.get("category") != manifest.category:
        raise AssertionError(f"{name}: plugin.json.category 与 MANIFEST.category 不一致")
    if metadata.get("interaction_profile") != manifest.interaction_profile:
        raise AssertionError(
            f"{name}: plugin.json.interaction_profile 与 MANIFEST.interaction_profile 不一致"
        )
    if list(metadata.get("interaction_entries") or []) != list(manifest.interaction_entries):
        raise AssertionError(f"{name}: plugin.json.interaction_entries 与 MANIFEST.interaction_entries 不一致")

    for field in ("permissions", "allowed_hosts"):
        expected = list(metadata.get(field) or [])
        actual = list(getattr(manifest, field))
        if expected != actual:
            raise AssertionError(f"{name}: plugin.json.{field} 与 MANIFEST.{field} 不一致")

    missing_permissions = sorted(REQUIRED_PERMISSIONS.get(name, set()) - set(manifest.permissions))
    if missing_permissions:
        raise AssertionError(f"{name}: 缺少必要权限: {', '.join(missing_permissions)}")

    print(f"ok: {name}")


def main() -> int:
    if not EXAMPLES_ROOT.is_dir():
        raise AssertionError(f"示例目录不存在: {EXAMPLES_ROOT}")

    present = {path.name for path in EXAMPLES_ROOT.iterdir() if path.is_dir()}
    unexpected = sorted(present - INCLUDED_EXAMPLES - set(SKIPPED_EXAMPLES))
    if unexpected:
        raise AssertionError(
            "发现未分类的插件示例，请加入 INCLUDED_EXAMPLES 或 SKIPPED_EXAMPLES: "
            + ", ".join(unexpected)
        )

    for name in sorted(INCLUDED_EXAMPLES):
        if name not in present:
            raise AssertionError(f"INCLUDED_EXAMPLES 中的示例不存在: {name}")
        _validate_example(name)

    for name in sorted(SKIPPED_EXAMPLES):
        if name in present:
            print(f"skip: {name} - {SKIPPED_EXAMPLES[name]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"plugin example validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
