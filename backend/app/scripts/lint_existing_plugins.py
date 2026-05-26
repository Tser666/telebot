"""存量 installed 插件 lint 回填脚本。

用法：
    python -m app.scripts.lint_existing_plugins --dry-run
    python -m app.scripts.lint_existing_plugins --only demo_plugin
"""

from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.plugin import InstalledPlugin, PluginInstall
from app.db.models.remote_plugin import RemotePlugin
from app.services.remote_plugin_service import lint_plugin_metadata_files
from app.settings import settings


@dataclass(frozen=True)
class LintTarget:
    source: str
    key: str
    path: Path


def _legacy_plugin_dir(name: str) -> Path:
    backend_root = Path(__file__).resolve().parents[2]
    return (backend_root / "plugins" / "installed" / name).resolve()


def _resolve_remote_plugin_dir(name: str) -> Path:
    current = (settings.plugins_installed_path / name).resolve()
    if current.exists():
        return current
    legacy = _legacy_plugin_dir(name)
    if legacy.exists():
        return legacy
    return current


def _merge_unique(existing: list[str], incoming: list[str]) -> list[str]:
    merged = list(existing)
    for item in incoming:
        if item not in merged:
            merged.append(item)
    return merged


def _render_diff(label: str, key: str, old: list[str], new: list[str]) -> str:
    if old == new:
        return f"[NOOP] {label}:{key} lint_warnings 未变化（{len(new)} 条）"
    return (
        f"[DIFF] {label}:{key}\n"
        f"  - old({len(old)}): {old}\n"
        f"  - new({len(new)}): {new}"
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对存量 installed 插件执行 metadata lint 并回填 lint_warnings")
    parser.add_argument("--dry-run", action="store_true", help="只打印 diff，不写数据库")
    parser.add_argument("--only", default=None, help="只处理指定插件 key（remote_plugin 用 name 匹配）")
    return parser.parse_args(argv)


async def _run_backfill(*, dry_run: bool, only: str | None) -> int:
    async with AsyncSessionLocal() as db:
        plugin_install_rows = (await db.execute(select(PluginInstall))).scalars().all()
        remote_plugin_rows = (await db.execute(select(RemotePlugin))).scalars().all()
        installed_plugin_rows = (await db.execute(select(InstalledPlugin))).scalars().all()

        targets: list[LintTarget] = []
        for row in plugin_install_rows:
            if row.installed_path:
                targets.append(LintTarget("plugin_install", row.key, Path(row.installed_path)))
        for row in installed_plugin_rows:
            if row.installed_path:
                targets.append(LintTarget("installed_plugin", row.key, Path(row.installed_path)))
        for row in remote_plugin_rows:
            targets.append(LintTarget("remote_plugin", row.name, _resolve_remote_plugin_dir(row.name)))

        if only:
            targets = [item for item in targets if item.key == only]
            remote_plugin_rows = [item for item in remote_plugin_rows if item.name == only]
            installed_plugin_rows = [item for item in installed_plugin_rows if item.key == only]

        warnings_by_key: dict[str, list[str]] = defaultdict(list)
        for target in targets:
            lint_items: list[str]
            if target.path.exists() and target.path.is_dir():
                lint_items = lint_plugin_metadata_files(target.path)
            else:
                lint_items = []
            warnings_by_key[target.key] = _merge_unique(warnings_by_key[target.key], lint_items)

        print(
            "扫描完成："
            f" plugin_install={len(plugin_install_rows)}"
            f" remote_plugin={len(remote_plugin_rows)}"
            f" installed_plugin={len(installed_plugin_rows)}"
            f" lint_targets={len(targets)}"
            f" only={only or '-'}"
            f" dry_run={dry_run}"
        )

        for row in remote_plugin_rows:
            new_warnings = list(warnings_by_key.get(row.name, []))
            old_warnings = list(row.lint_warnings or [])
            print(_render_diff("remote_plugin", row.name, old_warnings, new_warnings))
            if not dry_run:
                row.lint_warnings = new_warnings

        for row in installed_plugin_rows:
            new_warnings = list(warnings_by_key.get(row.key, []))
            old_warnings = list(row.lint_warnings or [])
            print(_render_diff("installed_plugin", row.key, old_warnings, new_warnings))
            if not dry_run:
                row.lint_warnings = new_warnings

        if dry_run:
            await db.rollback()
            print("dry-run 模式：未写入数据库。")
            return 0

        await db.commit()
        print("回填完成：已写入 remote_plugin / installed_plugin 的 lint_warnings。")
        return 0


def main() -> int:
    args = _parse_args()
    return asyncio.run(_run_backfill(dry_run=bool(args.dry_run), only=args.only))


if __name__ == "__main__":
    raise SystemExit(main())
