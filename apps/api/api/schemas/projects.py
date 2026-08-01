from pydantic import BaseModel, Field


class ProjectResponse(BaseModel):
    id: str
    name: str
    owner_id: str
    is_public: bool
    created_at: str
    is_mine: bool = False  # populated by the route, not stored


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_public: bool = False


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_public: bool | None = None
