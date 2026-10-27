from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import require_test_access
from ..traffic import traffic_store


router = APIRouter(
    prefix="/api/traffic",
    tags=["Traffic Dashboard"],
    dependencies=[Depends(require_test_access)],
)


@router.get(
    "/summary",
    summary="Read live traffic metrics and recent request samples",
)
async def traffic_summary(
    recent_limit: int = Query(default=40, ge=0, le=100),
) -> dict:
    return traffic_store.snapshot(recent_limit=recent_limit)


@router.delete("/clear", summary="Clear in-memory traffic metrics only")
async def clear_traffic() -> dict[str, bool]:
    traffic_store.clear()
    return {"cleared": True}

