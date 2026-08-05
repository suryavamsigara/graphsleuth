from supabase import Client

from engine.models.document import Chunk
from engine.models.document import Document, ReasoningTrace
from engine.models.edge import Edge
from engine.models.node import Node
from engine.ports.graph_store import GraphStore


class SupabaseGraphStore(GraphStore):
    def __init__(self, client: Client):
        self.client = client

    # -- Nodes --
    def save_node(self, node: Node) -> None:
        if not node.project_id:
            raise ValueError(f"Node {node.id} has no project_id set — refusing to save unscoped row")
        self.client.table("nodes").upsert({
            "id": node.id,
            "project_id": node.project_id,
            "node_type": node.node_type,
            "aliases": node.aliases,
            "description": node.description,
            "source_chunk_ids": node.source_chunk_ids,
            "created_at": node.created_at,
        }).execute()

    def load_nodes(self, project_id: str) -> dict[str, Node]:
        resp = self.client.table("nodes").select("*").eq("project_id", project_id).execute()
        return {row["id"]: self._row_to_node(row) for row in resp.data}

    def delete_node(self, node_id: str) -> bool:
        self.client.table("nodes").delete().eq("id", node_id).execute()
        return True

    # -- Edges --
    def save_edge(self, edge: Edge) -> bool:
        if not edge.project_id:
            raise ValueError(f"Edge {edge.id} has no project_id set — refusing to save unscoped row")
        try:
            self.client.table("edges").insert({
                "id": edge.id,
                "project_id": edge.project_id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relation": edge.relation,
                "source_chunk_id": edge.source_chunk_id,
                "created_at": edge.created_at,
            }).execute()
            return True
        except Exception as e:
            if "duplicate" in str(e).lower() or "23505" in str(e):
                return False
            raise

    def load_edges(self, project_id: str) -> list[Edge]:
        resp = self.client.table("edges").select("*").eq("project_id", project_id).execute()
        return [self._row_to_edge(row) for row in resp.data]

    def get_edges_from(self, node_id: str) -> list[Edge]:
        resp = self.client.table("edges").select("*").eq("source_id", node_id).execute()
        return [self._row_to_edge(row) for row in resp.data]

    def get_edges_to(self, node_id: str) -> list[Edge]:
        resp = self.client.table("edges").select("*").eq("target_id", node_id).execute()
        return [self._row_to_edge(row) for row in resp.data]

    def get_edges_between(self, source_id: str, target_id: str) -> list[Edge]:
        resp = self.client.table("edges").select("*") \
            .eq("source_id", source_id).eq("target_id", target_id).execute()
        return [self._row_to_edge(row) for row in resp.data]

    # -- Chunks --
    def save_chunk(self, chunk: Chunk) -> None:
        if not chunk.project_id:
            raise ValueError(f"Chunk {chunk.id} has no project_id set — refusing to save unscoped row")
        self.client.table("chunks").upsert({
            "id": chunk.id,
            "project_id": chunk.project_id,
            "text": chunk.text,
            "document_id": chunk.document_id,
            "idx": chunk.index,
        }).execute()

    def load_chunks(self, project_id: str) -> dict[str, Chunk]:
        resp = self.client.table("chunks").select("*").eq("project_id", project_id).execute()
        return {row["id"]: self._row_to_chunk(row) for row in resp.data}

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        resp = self.client.table("chunks").select("*").eq("id", chunk_id).execute()
        if not resp.data:
            return None
        return self._row_to_chunk(resp.data[0])

    # -- Documents --
    def save_document(self, doc: Document) -> None:
        if not doc.project_id:
            raise ValueError(f"Document {doc.id} has no project_id set — refusing to save unscoped row")
        self.client.table("documents").upsert({
            "id": doc.id,
            "project_id": doc.project_id,
            "path": doc.path,
            "name": doc.name,
            "checksum": doc.checksum,
            "ingested_at": doc.ingested_at,
        }).execute()

    def load_documents(self, project_id: str) -> dict[str, Document]:
        resp = self.client.table("documents").select("*").eq("project_id", project_id).execute()
        return {row["id"]: self._row_to_doc(row) for row in resp.data}

    def get_document_by_checksum(self, checksum: str, project_id: str) -> Document | None:
        resp = self.client.table("documents").select("*") \
            .eq("checksum", checksum).eq("project_id", project_id).execute()
        if not resp.data:
            return None
        return self._row_to_doc(resp.data[0])

    # -- Trace --
    def save_trace(self, ev: ReasoningTrace) -> str:
        if not ev.project_id:
            raise ValueError("ReasoningTrace has no project_id set — refusing to save unscoped row")
        d = ev.to_dict()
        self.client.table("traces").insert({
            "id": d["id"],
            "project_id": d["project_id"],
            "question": d["question"],
            "entry_nodes": d["entry_nodes"],
            "visited_nodes": d["visited_nodes"],
            "traversed_edges": d["traversed_edges"],
            "source_chunks": d["source_chunks"],
            "answer": d["answer"],
            "confidence": d["confidence"],
            "created_at": d["created_at"],
        }).execute()
        return d["id"]

    def load_traces_for_question(self, question: str, project_id: str, limit: int = 10) -> list[ReasoningTrace]:
        resp = self.client.table("traces").select("*") \
            .eq("question", question) \
            .eq("project_id", project_id) \
            .order("confidence", desc=True) \
            .limit(limit).execute()
        return [self._row_to_trace(row) for row in resp.data]

    def get_trace(self, trace_id: str) -> ReasoningTrace | None:
        resp = self.client.table("traces").select("*").eq("id", trace_id).execute()
        if not resp.data:
            return None
        return self._row_to_trace(resp.data[0])

    def close(self) -> None:
        pass

    # -- Helpers --
    @staticmethod
    def _row_to_node(row) -> Node:
        return Node.from_dict({
            "id": row["id"],
            "node_type": row["node_type"],
            "aliases": row["aliases"],
            "description": row["description"],
            "source_chunk_ids": row["source_chunk_ids"],
            "created_at": row["created_at"],
            "project_id": row.get("project_id"),
        })

    @staticmethod
    def _row_to_edge(row) -> Edge:
        return Edge.from_dict({
            "id": row["id"],
            "source_id": row["source_id"],
            "target_id": row["target_id"],
            "relation": row["relation"],
            "source_chunk_id": row["source_chunk_id"],
            "created_at": row["created_at"],
            "project_id": row.get("project_id"),
        })

    @staticmethod
    def _row_to_chunk(row) -> Chunk:
        return Chunk(
            id=row["id"],
            text=row["text"],
            document_id=row["document_id"],
            index=row["idx"],
            project_id=row.get("project_id"),
        )

    @staticmethod
    def _row_to_doc(row) -> Document:
        return Document.from_dict({
            "id": row["id"],
            "path": row["path"],
            "name": row["name"],
            "checksum": row["checksum"],
            "ingested_at": row["ingested_at"],
            "project_id": row.get("project_id"),
        })

    @staticmethod
    def _row_to_trace(row) -> ReasoningTrace:
        return ReasoningTrace.from_dict(row)