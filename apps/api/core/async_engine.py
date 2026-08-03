import asyncio
from typing import AsyncGenerator

from engine.ingestion.pipeline import IngestionPipeline
from engine.graph.knowledge_graph import KnowledgeGraph
from engine.agent.reasoner_async import AsyncGraphReasoner
from engine.models.document import EvidencePath


class AsyncEngine:
    """Thread-safe async wrapper around the sync knowledge graph."""

    def __init__(
        self,
        kg: KnowledgeGraph,
        pipeline: IngestionPipeline,
        agent: AsyncGraphReasoner,
        file_store,
    ):
        self.kg = kg
        self.pipeline = pipeline
        self.agent = agent
        self.file_store = file_store
        self._write_lock = asyncio.Lock()

    async def ingest_file(self, file_path: str, file_name: str) -> dict:
        async with self._write_lock:
            return await asyncio.to_thread(self.pipeline.ingest_file, file_path, file_name)

    async def query_stream(
        self,
        question: str,
        confidence_threshold: float | None = None,
        top_k: int | None = None,
        max_depth: int | None = None,
        history: list[dict] | None = None,
    ) -> AsyncGenerator[dict, None]:
        async for event in self.agent.answer_stream(
            question,
            confidence_threshold=confidence_threshold,
            top_k=top_k,
            max_depth=max_depth,
            history=history,
        ):
            yield event

    async def list_documents(self):
        return await asyncio.to_thread(lambda: list(self.kg.documents.values()))

    async def get_document(self, doc_id: str):
        return await asyncio.to_thread(lambda: self.kg.documents.get(doc_id))

    async def get_metrics(self):
        return await asyncio.to_thread(self.kg.get_metrics)

    async def get_node(self, node_id: str):
        return await asyncio.to_thread(self.kg.get_node, node_id)

    async def search_nodes(self, query: str, k: int = 5):
        return await asyncio.to_thread(self.kg.get_top_k_nodes, query, k)

    async def traverse(self, start_node_id: str, max_depth: int = 2, direction: str = "both"):
        return await asyncio.to_thread(
            self.kg.bfs_traversal, start_node_id, max_depth=max_depth, direction=direction
        )

    async def get_node_edges(self, node_id: str):
        """All edges touching a node, both directions, deduplicated."""
        return await asyncio.to_thread(self.kg.get_all_edges, node_id)

    async def get_chunk(self, chunk_id: str):
        return await asyncio.to_thread(self.kg.get_chunk, chunk_id)


    async def get_evidence_by_id(self, evidence_id: str) -> EvidencePath | None:
        return await asyncio.to_thread(self.kg.store.get_evidence, evidence_id)

    async def get_evidence_graph(self, evidence: EvidencePath) -> dict:
        def _build():
            node_ids = set(evidence.visited_nodes) | set(evidence.entry_nodes)
            nodes = []
            for nid in node_ids:
                n = self.kg.get_node(nid)
                if not n:
                    continue
                nodes.append(
                    {
                        "id": n.id,
                        "label": n.name,
                        "type": n.node_type,
                        "description": n.description,
                        "is_entry": nid in evidence.entry_nodes,
                    }
                )
            edges = [
                {"id": e.id, "source": e.source_id, "target": e.target_id, "label": e.relation}
                for e in evidence.traversed_edges
            ]
            return {"nodes": nodes, "edges": edges}

        return await asyncio.to_thread(_build)

