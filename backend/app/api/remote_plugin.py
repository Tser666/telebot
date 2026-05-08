"""远程插件管理 API 路由。"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..deps import DBSession
from ..schemas.remote_plugin import RemotePluginCreate, RemotePluginOut
from ..services import remote_plugin_service as svc
from ..services.remote_plugin_service import (
    DuplicatePluginName,
    GitOperationFailed,
    InvalidPluginMetadata,
    RemotePluginError,
    RemotePluginNotFound,
)

router = APIRouter(prefix="/api/remote-plugins", tags=["remote-plugins"])


@router.get("", response_model=list[RemotePluginOut])
async def list_remote_plugins(db: DBSession):
    """列出所有已安装远程插件。"""
    rows = await svc.list_installed(db)
    return rows


@router.post("/install", response_model=RemotePluginOut, status_code=201)
async def api_install_plugin(
    body: RemotePluginCreate, db: DBSession
):
    """从 Git URL 克隆并安装远程插件。"""
    try:
        row = await svc.install(db, body.source_url)
        await db.commit()
        await db.refresh(row)
        return row
    except DuplicatePluginName as e:
        raise HTTPException(409, detail={"code": e.code, "message": e.message}) from e
    except (GitOperationFailed, InvalidPluginMetadata) as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message}) from e
    except RemotePluginError as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message}) from e
    except Exception as e:
        raise HTTPException(500, detail={"code": "INTERNAL", "message": f"安装失败: {e}"}) from e


@router.post("/{name}/enable")
async def api_enable(name: str, db: DBSession):
    """启用指定远程插件。"""
    try:
        row = await svc.enable(db, name)
        await db.commit()
        return {"ok": True, "name": row.name, "enabled": True}
    except RemotePluginNotFound as e:
        raise HTTPException(404, detail={"code": e.code, "message": e.message}) from e


@router.post("/{name}/disable")
async def api_disable(name: str, db: DBSession):
    """禁用指定远程插件。"""
    try:
        row = await svc.disable(db, name)
        await db.commit()
        return {"ok": True, "name": row.name, "enabled": False}
    except RemotePluginNotFound as e:
        raise HTTPException(404, detail={"code": e.code, "message": e.message}) from e


@router.post("/{name}/update", response_model=RemotePluginOut)
async def api_update(name: str, db: DBSession):
    """从远程仓库 git pull 并更新插件元数据。"""
    try:
        row = await svc.update(db, name)
        await db.commit()
        await db.refresh(row)
        return row
    except RemotePluginNotFound as e:
        raise HTTPException(404, detail={"code": e.code, "message": e.message}) from e
    except (GitOperationFailed, InvalidPluginMetadata) as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message}) from e
    except RemotePluginError as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message}) from e


@router.delete("/{name}")
async def api_uninstall(name: str, db: DBSession):
    """卸载并删除指定远程插件。"""
    found = await svc.uninstall(db, name)
    if not found:
        raise HTTPException(
            404, detail={"code": "PLUGIN_NOT_FOUND", "message": f"插件 {name} 不存在"}
        )
    await db.commit()
    return {"ok": True, "name": name}
