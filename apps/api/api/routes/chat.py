from fastapi import APIRouter, Depends

from apps.api.core.auth import AuthedUser, get_current_user
from apps.api.core.chat_store import ChatStore
from apps.api.core.project_context import get_current_project
from apps.api.core.projects_store import Project
from apps.api.dependencies import get_supabase_client
from apps.api.api.schemas.chat import ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def get_chat_store() -> ChatStore:
    return ChatStore(client=get_supabase_client())


@router.get("/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    project: Project = Depends(get_current_project),  # must have read access to the project
    user: AuthedUser = Depends(get_current_user),
    store: ChatStore = Depends(get_chat_store),
):
    rows = store.list_messages(project.id, user.id)
    return [
        ChatMessageResponse(
            id=r.id,
            role=r.role,
            content=r.content,
            steps=r.steps,
            confidence=r.confidence,
            latency_ms=r.latency_ms,
            evidence_id=r.evidence_id,
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.delete("/messages")
async def clear_messages(
    project: Project = Depends(get_current_project),
    user: AuthedUser = Depends(get_current_user),
    store: ChatStore = Depends(get_chat_store),
):
    store.clear(project.id, user.id)
    return {"success": True}
