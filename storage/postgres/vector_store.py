import json
import psycopg
from pgvector.psycopg import register_vector

from engine.ports.vector_store import VectorStore

class PostgresVectorStore(VectorStore):
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn
        register_vector(self.conn)

    def upsert_node_embedding(self, node_id: str, embedding: list[float]) -> None:
        self.conn.execute(
            "UPDATE nodes SET embedding = (%s)::vector WHERE id = %s",
            (embedding, node_id),
    )

    def upsert_chunk_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        self.conn.execute(
            "UPDATE chunks SET embedding = (%s)::vector WHERE id = %s",
            (embedding, chunk_id),
        )

    def search_nodes(self, query_embedding: list[float], k: int = 5, threshold: float = 0.0) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            "SELECT id, similarity FROM match_nodes((%s)::vector, %s, %s)",
            (query_embedding, threshold, k)
        ).fetchall()

        return [(str(row["id"]), float(row["similarity"])) for row in rows]

    def search_chunks(self, query_embedding: list[float], k: int = 5, threshold: float = 0.0) -> list[tuple[str, float]]:
        rows = self.conn.execute(
            "SELECT id, similarity FROM match_chunks((%s)::vector, %s, %s)",
            (query_embedding, threshold, k)
        ).fetchall()
        
        return [(str(row["id"]), float(row["similarity"])) for row in rows]


    def get_node_embedding(self, node_id: str) -> list[float] | None:
        row = self.conn.execute("SELECT embedding FROM nodes WHERE id = %s", (node_id,)).fetchone()

        if row and row["embedding"] is not None:
            return row["embedding"].to_numpy().tolist()
        return None

    def get_chunk_embedding(self, chunk_id: str) -> list[float] | None:
        row = self.conn.execute("SELECT embedding FROM chunks WHERE id = %s", (chunk_id,)).fetchone()
        
        if row and row["embedding"] is not None:
            return row["embedding"].to_numpy().tolist()
        return None

    def close(self) -> None:
        self.conn.close()