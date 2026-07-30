from fastapi import APIRouter

from apps.api.dependencies import get_supabase_client

router = APIRouter()

@router.get("/")
def health():
    client = get_supabase_client()
    resp = client.table("nodes").select("id", count="exact").limit(1).execute()
    return {
        "status": "ok",
        "supabase_connected": True,
        "nodes_in_db": resp.count,
    }