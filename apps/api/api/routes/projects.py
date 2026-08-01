from fastapi import APIRouter, Depends, HTTPException

from apps.api.core.auth import AuthedUser, get_current_user, get_current_user_optional
from apps.api.core.projects_store import ProjectsStore
from apps.api.core.project_context import get_projects_store
from apps.api.api.schemas.projects import ProjectResponse, ProjectCreateRequest, ProjectUpdateRequest

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(p, viewer_id: str | None) -> ProjectResponse:
    return ProjectResponse(
        id=p.id,
        name=p.name,
        owner_id=p.owner_id,
        is_public=p.is_public,
        created_at=p.created_at,
        is_mine=(viewer_id is not None and p.owner_id == viewer_id),
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    user: AuthedUser | None = Depends(get_current_user_optional),
    store: ProjectsStore = Depends(get_projects_store),
):
    """Mine + public, for the workspace switcher. Works signed-out too
    (just returns the public gallery)."""
    projects = store.list_for_user(user.id if user else None)
    return [_to_response(p, user.id if user else None) for p in projects]


@router.get("/public", response_model=list[ProjectResponse])
async def list_public_projects(store: ProjectsStore = Depends(get_projects_store)):
    """Explicit public-only feed for the signed-out home page gallery."""
    projects = store.list_public()
    return [_to_response(p, None) for p in projects]


@router.post("/", response_model=ProjectResponse)
async def create_project(
    req: ProjectCreateRequest,
    user: AuthedUser = Depends(get_current_user),
    store: ProjectsStore = Depends(get_projects_store),
):
    project = store.create(name=req.name, owner_id=user.id, is_public=req.is_public)
    return _to_response(project, user.id)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: AuthedUser | None = Depends(get_current_user_optional),
    store: ProjectsStore = Depends(get_projects_store),
):
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.is_public and (not user or project.owner_id != user.id):
        raise HTTPException(status_code=403, detail="You don't have access to this case")
    return _to_response(project, user.id if user else None)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdateRequest,
    user: AuthedUser = Depends(get_current_user),
    store: ProjectsStore = Depends(get_projects_store),
):
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the case owner can edit it")
    updated = store.update(project_id, name=req.name, is_public=req.is_public)
    return _to_response(updated, user.id)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    user: AuthedUser = Depends(get_current_user),
    store: ProjectsStore = Depends(get_projects_store),
):
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the case owner can delete it")
    store.delete(project_id)
    return {"success": True}
