from dataclasses import dataclass
from supabase import Client


@dataclass
class Project:
    id: str
    name: str
    owner_id: str
    is_public: bool
    created_at: str


class ProjectsStore:
    def __init__(self, client: Client):
        self.client = client

    def create(self, name: str, owner_id: str, is_public: bool = False) -> Project:
        resp = self.client.table("projects").insert({
            "name": name,
            "owner_id": owner_id,
            "is_public": is_public,
        }).execute()
        return self._row_to_project(resp.data[0])

    def get(self, project_id: str) -> Project | None:
        resp = self.client.table("projects").select("*").eq("id", project_id).execute()
        if not resp.data:
            return None
        return self._row_to_project(resp.data[0])

    def list_for_user(self, user_id: str | None) -> list[Project]:
        """Every project the user owns, plus every public project,
        deduplicated. Powers both the workspace switcher (mine) and the
        home page gallery (public)."""
        public_resp = self.client.table("projects").select("*").eq("is_public", True).execute()
        rows = {row["id"]: row for row in public_resp.data}

        if user_id:
            owned_resp = self.client.table("projects").select("*").eq("owner_id", user_id).execute()
            for row in owned_resp.data:
                rows[row["id"]] = row

        return [self._row_to_project(r) for r in rows.values()]

    def list_public(self) -> list[Project]:
        resp = self.client.table("projects").select("*").eq("is_public", True).execute()
        return [self._row_to_project(r) for r in resp.data]

    def update(self, project_id: str, *, name: str | None = None, is_public: bool | None = None) -> Project | None:
        patch = {}
        if name is not None:
            patch["name"] = name
        if is_public is not None:
            patch["is_public"] = is_public
        if not patch:
            return self.get(project_id)
        resp = self.client.table("projects").update(patch).eq("id", project_id).execute()
        if not resp.data:
            return None
        return self._row_to_project(resp.data[0])

    def delete(self, project_id: str) -> None:
        self.client.table("projects").delete().eq("id", project_id).execute()

    @staticmethod
    def _row_to_project(row: dict) -> Project:
        return Project(
            id=row["id"],
            name=row["name"],
            owner_id=row["owner_id"],
            is_public=row["is_public"],
            created_at=row["created_at"],
        )
