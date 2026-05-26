"""backfill installed_plugin before making legacy plugin tables readonly

Revision ID: 0029
Revises: 0028
Create Date: 2026-05-27

PluginInstall and RemotePlugin are intentionally kept in place for one major
cycle. This migration copies their current install state into installed_plugin;
application writes move to installed_plugin after this revision.
"""

from __future__ import annotations

from alembic import op

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO installed_plugin (
            key, source, source_url, installed_path, version, manifest_json, enabled,
            signature_ok, trust_tier, source_label, last_install_error,
            last_load_error, lint_warnings
        )
        SELECT
            key,
            source,
            NULL,
            installed_path,
            COALESCE(version, '0.0.0'),
            manifest_json,
            COALESCE(enabled, false),
            signature_ok,
            CASE WHEN signature_ok IS true THEN 'verified' ELSE 'community' END,
            'ZIP',
            NULL,
            NULL,
            '[]'::jsonb
        FROM plugin_install
        ON CONFLICT (key) DO UPDATE SET
            source = EXCLUDED.source,
            source_url = EXCLUDED.source_url,
            installed_path = EXCLUDED.installed_path,
            version = EXCLUDED.version,
            manifest_json = EXCLUDED.manifest_json,
            enabled = EXCLUDED.enabled,
            signature_ok = EXCLUDED.signature_ok,
            trust_tier = EXCLUDED.trust_tier,
            source_label = EXCLUDED.source_label,
            last_install_error = EXCLUDED.last_install_error,
            last_load_error = EXCLUDED.last_load_error,
            lint_warnings = EXCLUDED.lint_warnings,
            updated_at = now()
        """
    )
    op.execute(
        """
        INSERT INTO installed_plugin (
            key, source, source_url, installed_path, version, manifest_json, enabled,
            signature_ok, trust_tier, source_label, last_install_error,
            last_load_error, lint_warnings
        )
        SELECT
            name,
            'git',
            source_url,
            NULL,
            COALESCE(version, '0.0.0'),
            jsonb_build_object(
                'name', name,
                'display_name', COALESCE(display_name, name),
                'description', COALESCE(description, ''),
                'author', COALESCE(author, ''),
                'version', COALESCE(version, '0.0.0'),
                '_telepilot_remote', jsonb_build_object(
                    'default_enabled', COALESCE(default_enabled, false),
                    'latest_version', latest_version,
                    'update_available', COALESCE(update_available, false),
                    'last_update_check_at', CASE
                        WHEN last_update_check_at IS NULL THEN NULL
                        ELSE to_jsonb(last_update_check_at::text)
                    END,
                    'last_update_check_error', last_update_check_error
                )
            ),
            COALESCE(enabled, false),
            NULL,
            'community',
            'Git',
            NULL,
            NULL,
            COALESCE(lint_warnings::jsonb, '[]'::jsonb)
        FROM remote_plugin
        ON CONFLICT (key) DO UPDATE SET
            source = EXCLUDED.source,
            source_url = EXCLUDED.source_url,
            version = EXCLUDED.version,
            manifest_json = EXCLUDED.manifest_json,
            enabled = EXCLUDED.enabled,
            signature_ok = EXCLUDED.signature_ok,
            trust_tier = EXCLUDED.trust_tier,
            source_label = EXCLUDED.source_label,
            lint_warnings = EXCLUDED.lint_warnings,
            updated_at = now()
        """
    )


def downgrade() -> None:
    # Data backfill is intentionally not reversed; legacy tables remain intact.
    pass
