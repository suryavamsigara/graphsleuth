from fastapi import APIRouter, Depends

from apps.api.core.async_engine import AsyncEngine
from apps.api.dependencies import get_engine

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/")
async def health(engine: AsyncEngine = Depends(get_engine)):
    metrics = await engine.get_metrics()
    return {
        "status": "ok",
        "graph": metrics,
    }