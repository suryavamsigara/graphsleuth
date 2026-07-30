from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from apps.api.core.async_engine import AsyncEngine
from apps.api.dependencies import get_engine
from apps.api.api.schemas.query import QueryRequest

router = APIRouter(prefix="/query", tags=["query"])


async def _stream_answer(engine: AsyncEngine, question: str, top_k: int, max_depth: int):
    """SSE generator yielding JSON events."""
    async for event in engine.query_stream(question):
        yield {"data": event}


@router.post("/stream")
async def query_stream(
    req: QueryRequest,
    engine: AsyncEngine = Depends(get_engine),
):
    """Stream the agent's reasoning and answer via SSE."""
    return EventSourceResponse(
        _stream_answer(engine, req.question, req.top_k, req.max_depth),
        media_type="text/event-stream",
    )


@router.post("/")
async def query_sync(
    req: QueryRequest,
    engine: AsyncEngine = Depends(get_engine),
):
    """Non-streaming query: collects all events and returns final answer."""
    answer = ""
    evidence_id = None
    steps = []
    tokens_used = 0
    latency_ms = 0

    async for event in engine.query_stream(req.question):
        if event.get("type") == "token":
            answer += event.get("token", "")
        elif event.get("type") == "done":
            evidence_id = event.get("evidence_id")
            steps = event.get("steps", [])
            tokens_used = event.get("tokens_used", 0)
            latency_ms = event.get("latency_ms", 0)

    if not answer:
        raise HTTPException(status_code=404, detail="No answer generated")

    return {
        "answer": answer,
        "evidence_id": evidence_id,
        "steps": steps,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
    }