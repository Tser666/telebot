"""功能矩阵与账号-功能开关 REST API（PRD §9.2）。

Endpoint：
  - GET  /api/feature-matrix                      → 一次返回 N×M 矩阵
  - GET  /api/accounts/{aid}/features            → 该账号所有 feature 开关
  - PATCH /api/accounts/{aid}/features/{key}     → 启停或调整 config
  - GET  /api/plugins/{key}/config                → 获取 global config
  - PUT  /api/plugins/{key}/config               → 设置 global config
  - GET  /api/accounts/{aid}/features/{key}/config → 获取最终生效配置
  - POST /api/plugins/{key}/config/validate       → 验证配置是否符合 schema
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..db.models.account import Account
from ..db.models.feature import AccountFeature, Feature
from ..deps import CurrentUser, DBSession
from ..schemas.feature import (
    AccountFeatureConfigUpdate,
    AccountFeatureItem,
    AccountFeatureToggle,
    ConfigValidationResponse,
    FeatureMatrixResponse,
    PluginGlobalConfigResponse,
    PluginGlobalConfigUpdate,
)
from ..services import audit, feature_service
from ..services.redactor import is_sensitive_key, redact_value

router = APIRouter(tags=["features"])


def _bad(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _sanitize_config(config: dict[str, object]) -> dict[str, object]:
    return redact_value(config)


def _preserve_existing_sensitive_values(
    existing: dict[str, object] | None, incoming: dict[str, object]
) -> dict[str, object]:
    merged = dict(incoming)
    existing_dict = dict(existing or {})
    for key, value in existing_dict.items():
        if not is_sensitive_key(str(key)):
            continue
        if key not in merged or merged.get(key) in ("", None):
            merged[key] = value
    return merged


# ─────────────────────────────────────────────────────
# 矩阵
# ─────────────────────────────────────────────────────
@router.get("/api/feature-matrix", response_model=FeatureMatrixResponse)
async def get_feature_matrix(db: DBSession, _user: CurrentUser) -> FeatureMatrixResponse:
    """返回 N(账号) × M(功能) 矩阵。"""
    data = await feature_service.feature_matrix(db)
    return FeatureMatrixResponse(**data)


# ─────────────────────────────────────────────────────
# 单账号 feature 列表
# ─────────────────────────────────────────────────────
@router.get(
    "/api/accounts/{aid}/features",
    response_model=list[AccountFeatureItem],
)
async def list_account_features(
    aid: int, db: DBSession, _user: CurrentUser
) -> list[AccountFeatureItem]:
    """列出该账号所有 ``account_feature`` 行。"""
    if await db.get(Account, aid) is None:
        raise _bad("ACCOUNT_NOT_FOUND", "账号不存在", 404)
    rows = await feature_service.get_account_features(db, aid)
    return [
        AccountFeatureItem(
            feature_key=r.feature_key,
            enabled=r.enabled,
            state=r.state,
            last_error=r.last_error,
            config=_sanitize_config(dict(r.config or {})),
        )
        for r in rows
    ]


# ─────────────────────────────────────────────────────
# 启停 / 改 config
# ─────────────────────────────────────────────────────
@router.patch(
    "/api/accounts/{aid}/features/{key}",
    response_model=AccountFeatureItem,
)
async def patch_account_feature(
    aid: int,
    key: str,
    payload: AccountFeatureToggle,
    db: DBSession,
    user: CurrentUser,
) -> AccountFeatureItem:
    """启用 / 禁用某 feature，或更新它的 config。

    若 feature key 在 ``feature`` 表里没有登记，会拒绝（避免误开未知插件）。
    若提供了 config，会验证 JSON Schema 并保存。
    """
    if await db.get(Account, aid) is None:
        raise _bad("ACCOUNT_NOT_FOUND", "账号不存在", 404)
    # 校验 feature 存在（首次调用矩阵或 list 时已 seed 过；这里也 seed 一次以幂等）
    await feature_service.seed_builtin_features(db)
    feature = await db.get(Feature, key)
    if feature is None:
        raise _bad("FEATURE_NOT_FOUND", f"未注册的 feature: {key}", 404)

    # 如果提供了 config，验证 JSON Schema
    if payload.config is not None:
        existing = await db.get(AccountFeature, (aid, key))
        payload.config = _preserve_existing_sensitive_values(
            dict(existing.config or {}) if existing is not None else None,
            dict(payload.config),
        )
        config_schema = (feature.manifest or {}).get("config_schema")
        if config_schema:
            validation = feature_service.validate_config_against_schema(
                payload.config, config_schema
            )
            if not validation.valid:
                raise _bad(
                    "CONFIG_VALIDATION_ERROR",
                    f"配置验证失败: {'; '.join(f'{e.field}: {e.message}' for e in validation.errors)}",
                )

    af = await feature_service.set_account_feature(
        db, aid, key, enabled=payload.enabled, config=payload.config
    )
    await audit.write(
        db,
        user.id,
        "feature.toggle",
        target=f"account:{aid}/feature:{key}",
        detail={"enabled": payload.enabled},
    )
    await db.commit()
    return AccountFeatureItem(
        feature_key=af.feature_key,
        enabled=af.enabled,
        state=af.state,
        last_error=af.last_error,
        config=_sanitize_config(dict(af.config or {})),
    )


# ─────────────────────────────────────────────────────
# 账号级配置更新（仅更新 config，不改变 enabled）
# ─────────────────────────────────────────────────────
@router.patch(
    "/api/accounts/{aid}/features/{key}/config",
    response_model=AccountFeatureItem,
)
async def update_account_feature_config(
    aid: int,
    key: str,
    payload: AccountFeatureConfigUpdate,
    db: DBSession,
    user: CurrentUser,
) -> AccountFeatureItem:
    """仅更新账号级配置，不改变 enabled 状态。

    会验证 JSON Schema 并保存。
    """
    if await db.get(Account, aid) is None:
        raise _bad("ACCOUNT_NOT_FOUND", "账号不存在", 404)
    await feature_service.seed_builtin_features(db)
    feature = await db.get(Feature, key)
    if feature is None:
        raise _bad("FEATURE_NOT_FOUND", f"未注册的 feature: {key}", 404)

    # 验证 JSON Schema
    existing = await db.get(AccountFeature, (aid, key))
    payload.config = _preserve_existing_sensitive_values(
        dict(existing.config or {}) if existing is not None else None,
        dict(payload.config),
    )
    config_schema = (feature.manifest or {}).get("config_schema")
    if config_schema:
        validation = feature_service.validate_config_against_schema(
            payload.config, config_schema
        )
        if not validation.valid:
            raise _bad(
                "CONFIG_VALIDATION_ERROR",
                f"配置验证失败: {'; '.join(f'{e.field}: {e.message}' for e in validation.errors)}",
            )

    af = await feature_service.set_account_feature(
        db, aid, key, enabled=True, config=payload.config
    )
    await audit.write(
        db,
        user.id,
        "feature.config.update",
        target=f"account:{aid}/feature:{key}",
        detail={"config_keys": sorted(payload.config.keys())},
    )
    await db.commit()
    return AccountFeatureItem(
        feature_key=af.feature_key,
        enabled=af.enabled,
        state=af.state,
        last_error=af.last_error,
        config=_sanitize_config(dict(af.config or {})),
    )


# ─────────────────────────────────────────────────────
# Global Config API
# ─────────────────────────────────────────────────────
@router.get(
    "/api/plugins/{key}/config",
    response_model=PluginGlobalConfigResponse,
)
async def get_plugin_global_config(
    key: str,
    db: DBSession,
    _user: CurrentUser,
) -> PluginGlobalConfigResponse:
    """获取插件的 global config。"""
    await feature_service.seed_builtin_features(db)
    feature = await db.get(Feature, key)
    if feature is None:
        raise _bad("FEATURE_NOT_FOUND", f"未注册的插件: {key}", 404)

    global_config = await feature_service.get_plugin_global_config(db, key)
    return PluginGlobalConfigResponse(
        plugin_key=key,
        config=_sanitize_config(global_config),
        global_config=_sanitize_config(global_config),
    )


@router.put(
    "/api/plugins/{key}/config",
    response_model=PluginGlobalConfigResponse,
)
async def set_plugin_global_config(
    key: str,
    payload: PluginGlobalConfigUpdate,
    db: DBSession,
    user: CurrentUser,
) -> PluginGlobalConfigResponse:
    """设置插件的 global config。

    - 验证配置是否符合 config_schema。
    - 仅更新标记为 level="global" 的字段。
    - 通知所有使用该插件的账号的 worker reload。
    """
    try:
        global_config = await feature_service.set_plugin_global_config(
            db, key, payload.config
        )
    except ValueError as e:
        raise _bad("CONFIG_VALIDATION_ERROR", str(e)) from e

    await audit.write(
        db,
        user.id,
        "feature.global_config.update",
        target=f"plugin:{key}",
        detail={"global_config_keys": sorted(global_config.keys())},
    )
    await db.commit()

    return PluginGlobalConfigResponse(
        plugin_key=key,
        config=_sanitize_config(global_config),
        global_config=_sanitize_config(global_config),
    )


# ─────────────────────────────────────────────────────
# 获取账号级最终生效配置（合并后）
# ─────────────────────────────────────────────────────
@router.get(
    "/api/accounts/{aid}/features/{key}/config",
    response_model=dict[str, object],
)
async def get_effective_config(
    aid: int,
    key: str,
    db: DBSession,
    _user: CurrentUser,
) -> dict[str, object]:
    """获取某账号某插件的最终生效配置。

    合并顺序：schema defaults < global config < account config
    """
    if await db.get(Account, aid) is None:
        raise _bad("ACCOUNT_NOT_FOUND", "账号不存在", 404)
    await feature_service.seed_builtin_features(db)
    feature = await db.get(Feature, key)
    if feature is None:
        raise _bad("FEATURE_NOT_FOUND", f"未注册的 feature: {key}", 404)

    effective_config = await feature_service.get_effective_plugin_config(db, aid, key)
    return _sanitize_config(effective_config)


# ─────────────────────────────────────────────────────
# 配置验证
# ─────────────────────────────────────────────────────
@router.post(
    "/api/plugins/{key}/config/validate",
    response_model=ConfigValidationResponse,
)
async def validate_plugin_config(
    key: str,
    payload: PluginGlobalConfigUpdate,
    db: DBSession,
    _user: CurrentUser,
) -> ConfigValidationResponse:
    """验证配置是否符合插件的 config_schema。"""
    await feature_service.seed_builtin_features(db)
    feature = await db.get(Feature, key)
    if feature is None:
        raise _bad("FEATURE_NOT_FOUND", f"未注册的插件: {key}", 404)

    config_schema = (feature.manifest or {}).get("config_schema")
    if not config_schema:
        return {"valid": True, "errors": []}

    return feature_service.validate_config_against_schema(payload.config, config_schema)


__all__ = ["router"]
