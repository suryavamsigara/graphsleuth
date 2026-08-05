import json
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from apps.api.core.async_engine import AsyncEngine
from apps.api.core.auth import AuthedUser, get_current_user_optional
from apps.api.core.chat_store import ChatStore
from apps.api.core.project_context import get_current_project
from apps.api.core.projects_store import Project
from apps.api.dependencies import get_engine_for_read, get_supabase_client
from apps.api.api.schemas.query import QueryRequest

router = APIRouter(prefix="/query", tags=["query"])


def get_chat_store() -> ChatStore:
    return ChatStore(client=get_supabase_client())


async def _stream_answer(
    engine: AsyncEngine,
    req: QueryRequest,
    project: Project,
    user: AuthedUser | None,
    chat_store: ChatStore,
):
    """SSE generator yielding JSON events.
    Persistence: only signed-in users get their chat saved. Persisting happens right here, once
    the turn's `done` event is in hand — single source of truth.
    """
    history = []
    if user is not None:
        rows = await asyncio.to_thread(chat_store.list_messages, project.id, user.id, 6)
        history = [{"role": r.role, "content": r.content} for r in rows]

    async for event in engine.query_stream(
        req.question,
        confidence_threshold=req.confidence_threshold,
        top_k=req.top_k,
        max_depth=req.max_depth,
        history=history,
    ):
        if event.get("type") == "done" and user is not None:
            chat_store.save_turn(
                project_id=project.id,
                user_id=user.id,
                question=req.question,
                answer=event.get("answer", ""),
                steps=event.get("steps", []),
                confidence=event.get("confidence", 0.0),
                latency_ms=event.get("latency_ms", 0.0),
                trace_id=event.get("trace_id"),
            )
        yield {"data": json.dumps(event)}


@router.post("/stream")
async def query_stream(
    req: QueryRequest,
    project: Project = Depends(get_current_project),
    user: AuthedUser | None = Depends(get_current_user_optional),
    engine: AsyncEngine = Depends(get_engine_for_read),
    chat_store: ChatStore = Depends(get_chat_store),
):
    """Stream the agent's reasoning and answer via SSE."""
    return EventSourceResponse(
        _stream_answer(engine, req, project, user, chat_store),
        media_type="text/event-stream",
    )


@router.post("/")
async def query_sync(
    req: QueryRequest,
    project: Project = Depends(get_current_project),
    user: AuthedUser | None = Depends(get_current_user_optional),
    engine: AsyncEngine = Depends(get_engine_for_read),
    chat_store: ChatStore = Depends(get_chat_store),
):
    """Non-streaming query: collects all events and returns final answer."""
    answer = ""
    trace_id = None
    steps = []
    tokens_used = 0
    latency_ms = 0
    confidence = 0.0

    async for event in engine.query_stream(
        req.question,
        confidence_threshold=req.confidence_threshold,
        top_k=req.top_k,
        max_depth=req.max_depth,
    ):
        if event.get("type") == "token":
            answer += event.get("token", "")
        elif event.get("type") == "done":
            trace_id = event.get("trace_id")
            steps = event.get("steps", [])
            tokens_used = event.get("tokens_used", 0)
            latency_ms = event.get("latency_ms", 0)
            confidence = event.get("confidence", 0.0)

    if not answer:
        raise HTTPException(status_code=404, detail="No answer generated")

    if user is not None:
        chat_store.save_turn(
            project_id=project.id,
            user_id=user.id,
            question=req.question,
            answer=answer,
            steps=steps,
            confidence=confidence,
            latency_ms=latency_ms,
            trace_id=trace_id,
        )

    return {
        "answer": answer,
        "trace_id": trace_id,
        "steps": steps,
        "tokens_used": tokens_used,
        "latency_ms": latency_ms,
        "confidence": confidence,
    }
