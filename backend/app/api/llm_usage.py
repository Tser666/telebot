"""LLM 调用记录查询 API。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from ..db.models.llm_usage import LLMUsage
from ..deps import CurrentUser, DBSession

router = APIRouter(prefix="/api/llm/usage", tags=["llm-usage"])


class LLMUsageItem(BaseModel):
    """最近一次 LLM 调用记录。"""

    id: int
    account_id: int | None
    provider_id: int | None
    provider_name: str | None
    model: str | None
    source: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    success: bool
    error_type: str | None
    used_fallback: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LLMUsageSummary(BaseModel):
    """最近调用摘要。"""

    request_count: int
    success_count: int
    failed_count: int
    fallback_count: int
    total_tokens: int
    avg_latency_ms: int


class LLMUsageRecentResponse(BaseModel):
    """最近 LLM 调用记录列表。"""

    items: list[LLMUsageItem]
    summary: LLMUsageSummary


@router.get("/recent", response_model=LLMUsageRecentResponse)
async def list_recent_llm_usage(
    db: DBSession,
    _user: CurrentUser,
    limit: int = Query(20, ge=1, le=100),
) -> LLMUsageRecentResponse:
    """返回最近 LLM 调用记录与摘要，供 AI 中心 Usage 页展示。"""
    rows = (
        await db.execute(
            select(LLMUsage)
            .order_by(LLMUsage.created_at.desc(), LLMUsage.id.desc())
            .limit(limit)
        )
    ).scalars().all()

    items = [LLMUsageItem.model_validate(row) for row in rows]
    request_count = len(items)
    success_count = sum(1 for item in items if item.success)
    failed_count = request_count - success_count
    fallback_count = sum(1 for item in items if item.used_fallback)
    total_tokens = sum(item.input_tokens + item.output_tokens for item in items)
    avg_latency_ms = int(sum(item.latency_ms for item in items) / request_count) if request_count else 0

    return LLMUsageRecentResponse(
        items=items,
        summary=LLMUsageSummary(
            request_count=request_count,
            success_count=success_count,
            failed_count=failed_count,
            fallback_count=fallback_count,
            total_tokens=total_tokens,
            avg_latency_ms=avg_latency_ms,
        ),
    )
