"""远程插件 Pydantic schemas。"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RemotePluginCreate(BaseModel):
    source_url: str
    default_enabled: bool = False


class RemotePluginOut(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    author: str
    source_url: str
    version: str
    enabled: bool
    default_enabled: bool = False
    installed_at: datetime | None = None

    class Config:
        from_attributes = True


class RegistryPluginOut(BaseModel):
    name: str
    display_name: str
    description: str
    author: str
    source_url: str
    version: str
    installed: bool
