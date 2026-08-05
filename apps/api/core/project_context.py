from fastapi import Depends, Header, HTTPException

from apps.api.core.auth import AuthedUser, get_current_user, get_current_user_optional
from apps.api.core.projects_store import Project, ProjectsStore


def get_projects_store() -> ProjectsStore:
    # avoids a circular import with dependencies.py
    from apps.api.dependencies import get_supabase_client
    return ProjectsStore(client=get_supabase_client())


async def get_project_id_header(x_project_id: str = Header(..., alias="X-Project-Id")) -> str:
    return x_project_id


async def get_current_project(
    project_id: str = Depends(get_project_id_header),
    user: AuthedUser | None = Depends(get_current_user_optional),
    store: ProjectsStore = Depends(get_projects_store),
) -> Project:
    """
    The authorization gate for every graph/document/query route.

    - Public project -> anyone can read it, authenticated or not.
    - Private project -> only the owner, and only if authenticated.
    """
    project = store.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.is_public:
        return project

    if user is None:
        raise HTTPException(status_code=401, detail="This project is private — sign in to access it")

    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this project")

    return project


async def require_project_owner(
    project: Project = Depends(get_current_project),
    user: AuthedUser = Depends(get_current_user),
) -> Project:
    """Stricter gate for writes (ingesting documents, running queries that
    persist trace into the project). Public+readable is not the same as
    writable — only the owner writes."""
    if project.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the project owner can modify it")
    return project
