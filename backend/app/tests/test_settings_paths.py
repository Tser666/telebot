from __future__ import annotations

from pathlib import Path

from app import settings as settings_module
from app.settings import Settings


def _settings(**overrides: object) -> Settings:
    return Settings(
        master_key="test-master-key",
        jwt_secret="test-jwt-secret",
        **overrides,
    )


def test_container_legacy_plugins_path_is_normalized(monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "PROJECT_ROOT", Path("/app"))

    settings = _settings(plugins_installed_dir="/plugins/installed")

    assert settings.plugins_installed_path == Path("/app/plugins/installed")


def test_container_legacy_plugin_repo_cache_path_is_normalized(monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "PROJECT_ROOT", Path("/app"))
    settings = _settings(plugin_repos_cache_dir="/data/plugin_repos")

    assert settings.resolve_project_path(settings.plugin_repos_cache_dir) == Path("/app/data/plugin_repos")


def test_non_legacy_absolute_path_is_kept(monkeypatch) -> None:
    monkeypatch.setattr(settings_module, "PROJECT_ROOT", Path("/app"))
    settings = _settings(plugins_installed_dir="/mnt/telepilot/plugins")

    assert settings.plugins_installed_path == Path("/mnt/telepilot/plugins")
