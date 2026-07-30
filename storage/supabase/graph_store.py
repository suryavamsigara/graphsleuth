import json
from supabase import Client

from engine.models.document import Chunk
from engine.models.document import Document, EvidencePath
from engine.models.edge import Edge
from engine.models.node import Node
from engine.ports.graph_store import GraphStore


class SupabaseGraphStore(GraphStore):
    def __init__(self, client: Client):
        self.client = client

    # -- Nodes --
    def save_node(self, node: Node) -> None:
        self.client.table("nodes").upsert({
            "id": node.id,
            "node_type": node.node_type,
            "aliases": node.aliases,
            "description": node.description,
            "source_chunk_ids": node.source_chunk_ids,
            "created_at": node.created_at,
        }).execute()

    def load_nodes(self):
        resp = self.client.table("nodes").select("*").execute()
        return {row["id"]: self._row_to_node(row) for row in resp.data}

    def delete_node(self, node_id: str) -> bool:
        self.client.table("nodes").delete().eq("id", node_id).execute()
        return True

    # -- Edges --
    def save_edge(self, edge: Edge) -> bool:
        try:
            self.client.table("edges").insert({
                "id": edge.id,
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

    def load_edges(self) -> list[Edge]:
        resp = self.client.table("edges").select("*").execute()
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
        self.client.table("chunks").upsert({
            "id": chunk.id,
            "text": chunk.text,
            "document_id": chunk.document_id,
            "idx": chunk.index,
        }).execute()

    def load_chunks(self) -> dict[str, Chunk]:
        resp = self.client.table("chunks").select("*").execute()
        return {row["id"]: self._row_to_chunk(row) for row in resp.data}

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        resp = self.client.table("chunks").select("*").eq("id", chunk_id).execute()
        if not resp.data:
            return None
        return self._row_to_chunk(resp.data[0])

    # -- Documents --
    def save_document(self, doc: Document) -> None:
        self.client.table("documents").upsert({
            "id": doc.id,
            "path": doc.path,
            "name": doc.name,
            "checksum": doc.checksum,
            "ingested_at": doc.ingested_at,
        }).execute()

    def load_documents(self) -> dict[str, Document]:
        resp = self.client.table("documents").select("*").execute()
        return {row["id"]: self._row_to_doc(row) for row in resp.data}

    def get_document_by_checksum(self, checksum: str) -> Document | None:
        resp = self.client.table("documents").select("*").eq("checksum", checksum).execute()
        if not resp.data:
            return None
        return self._row_to_doc(resp.data[0])


    # -- Evidence --
    def save_evidence(self, ev: EvidencePath) -> str:
        d = ev.to_dict()
        self.client.table("evidence_paths").insert({
            "id": d["id"],
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

    def load_evidence_for_question(self, question: str, limit: int = 10) -> list[EvidencePath]:
        resp = self.client.table("evidence_paths").select("*") \
            .eq("question", question) \
            .order("confidence", desc=True) \
            .limit(limit).execute()
        return [self._row_to_evidence(row) for row in resp.data]

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
        })

    @staticmethod
    def _row_to_chunk(row) -> Chunk:
        return Chunk(id=row["id"], text=row["text"], document_id=row["document_id"], index=row["idx"])

    @staticmethod
    def _row_to_doc(row) -> Document:
        return Document.from_dict({
            "id": row["id"],
            "path": row["path"],
            "name": row["name"],
            "checksum": row["checksum"],
            "ingested_at": row["ingested_at"],
        })

    @staticmethod
    def _row_to_evidence(row) -> EvidencePath:
        return EvidencePath.from_dict(row)