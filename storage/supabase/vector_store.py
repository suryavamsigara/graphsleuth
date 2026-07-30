import json
from supabase import Client
from engine.ports.vector_store import VectorStore

class SupabaseVectorStore(VectorStore):
    def __init__(self, client: Client):
        self.client = client

    def upsert_node_embedding(self, node_id: str, embedding: list[float]):
        self.client.table("nodes").update({"embedding": embedding}).eq("id", node_id).execute()

    def upsert_chunk_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        self.client.table("chunks").update({"embedding": embedding}).eq("id", chunk_id).execute()

    def search_nodes(self, query_embedding: list[float], k: int = 5, threshold: float = 0.0) -> list[tuple[str, float]]:
        resp = self.client.rpc("match_nodes", {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": k,
        }).execute()
        return [(row["id"], row["similarity"]) for row in resp.data]

    def search_chunks(self, query_embedding: list[float], k: int = 5, threshold: float = 0.0) -> list[tuple[str, float]]:
        resp = self.client.rpc("match_chunks", {
            "query_embedding": query_embedding,
            "match_threshold": threshold,
            "match_count": k,
        }).execute()
        return [(row["id"], row["similarity"]) for row in resp.data]

    def get_node_embedding(self, node_id: str) -> list[float] | None:
        resp = self.client.table("nodes").select("embedding").eq("id", node_id).execute()
        if not resp.data:
            return None
        raw_emb = resp.data[0]["embedding"]
        if isinstance(raw_emb, str):
            return json.loads(raw_emb)
        return list(raw_emb)

    def get_chunk_embedding(self, chunk_id: str) -> list[float] | None:
        resp = self.client.table("chunks").select("embedding").eq("id", chunk_id).execute()
        if not resp.data:
            return None
        raw_emb = resp.data[0]["embedding"]
        
        if isinstance(raw_emb, str):
            return json.loads(raw_emb)
        return list(raw_emb)