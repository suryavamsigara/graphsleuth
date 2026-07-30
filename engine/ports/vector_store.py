from typing import Protocol

class VectorStore(Protocol):
    def upsert_node_embedding(self, node_id: str, embedding: list[float]) -> None:
        ...

    def upsert_chunk_embedding(self, chunk_id: str, embedding: list[float]) -> None:
        ...

    def search_nodes(self, query_embedding: list[float], k: int, threshold: float) -> list[tuple[str, float]]:
        ...

    def search_chunks(self, query_embedding: list[float], k: int = 5, threshold: float = 0.0) -> list[tuple[str, float]]:
        ...

    def get_node_embedding(self, node_id: str) -> list[float] | None:
        ...

    def get_chunk_embedding(self, chunk_id: str) -> list[float] | None:
        ...