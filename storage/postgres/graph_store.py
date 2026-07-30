import psycopg
from psycopg.rows import dict_row
from pathlib import Path

from engine.models.node import Node
from engine.models.edge import Edge
from engine.models.document import Chunk, Document, EvidencePath
from engine.ports.graph_store import GraphStore

class PostgresGraphStore(GraphStore):
    """Full implementation"""
    def __init__(self, dsn: str):
        self.dsn = dsn
        self._conn = psycopg.connect(dsn, row_factory=dict_row)
        self._init_schema()

    def _init_schema(self) -> None:
        schema_path = Path(__file__).with_suffix(".sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            with self._conn.cursor() as cur:
                cur.execute(f.read())
        self._conn.commit()

    def save_node(self, node: Node) -> None:
        self._conn.execute(
            """
            INSERT INTO nodes (id, node_type, aliases, description, source_chunk_ids, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                node_type = EXCLUDED.node_type,
                aliases = EXCLUDED.aliases,
                description = EXCLUDED.description,
                source_chunk_ids = EXCLUDED.source_chunk_ids,
                created_at = EXCLUDED.created_at
            """,
            (
                node.id,
                node.node_type,
                node.aliases,
                node.description,
                node.source_chunk_ids,
                node.created_at,
            )
        )
        self._conn.commit()

    def load_nodes(self) -> list[str, Node]:
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return {
            str(row["id"]): Node.from_dict({
                "id": str(row["id"]),
                "node_type": row["node_type"],
                "aliases": row["aliases"],
                "description": row["description"],
                "source_chunk_ids": [str(uid) for uid in row["source_chunk_ids"]],
                "created_at": row["created_at"],
            })
            for row in rows
        }

    def delete_node(self, node_id: str) -> bool:
        self._conn.execute("DELETE FROM nodes WHERE id = %s", (node_id,))
        self._conn.commit()
        return True

    # Edges

    def save_edge(self, edge: Edge) -> bool:
        try:
            self._conn.execute(
                """
                INSERT INTO edges (id, source_id, target_id, relation, source_chunk_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    edge.id,
                    edge.source_id,
                    edge.target_id,
                    edge.relation,
                    edge.source_chunk_id,
                    edge.created_at,
                ),
            )
            self._conn.commit()
            return True
        except psycopg.IntegrityError:
            self._conn.rollback()
            return False

    def load_edges(self) -> list[Edge]:
        rows = self._conn.execute("SELECT * FROM edges").fetchall()
        return [self._row_to_edge(row) for row in rows]

    def get_edges_from(self, node_id: str) -> list[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE source_id = %s", (node_id,)
        ).fetchall()
        return [self._row_to_edge(row) for row in rows]


    def get_edges_to(self, node_id: str) -> list[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE target_id = %s", (node_id,)
        ).fetchall()
        return [self._row_to_edge(row) for row in rows]

    def get_edges_between(self, source_id: str, target_id: str) -> list[Edge]:
        rows = self._conn.execute(
            "SELECT * FROM edges WHERE source_id = %s AND target_id = %s",
            (source_id, target_id),
        ).fetchall()
        return [self._row_to_edge(row) for row in rows]

    # Chunks
    def save_chunk(self, chunk: Chunk) -> None:
        self._conn.execute(
            """
            INSERT INTO chunks (id, text, document_id, idx)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                text = EXCLUDED.text,
                document_id = EXCLUDED.document_id,
                idx = EXCLUDED.idx
            """,
            (chunk.id, chunk.text, chunk.document_id, chunk.index),
        )
        self._conn.commit()

    def load_chunks(self) -> dict[str, Chunk]:
        rows = self._conn.execute("SELECT * FROM chunks").fetchall()
        return {
            str(row["id"]): Chunk(
                id=str(row["id"]),
                text=row["text"],
                document_id=str(row["document_id"]),
                index=row["idx"],
            )
            for row in rows
        }

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        row = self._conn.execute(
            "SELECT * FROM chunks WHERE id = %s", (chunk_id,)
        ).fetchone()
        if row is None:
            return None
        return Chunk(
            id=str(row["id"]),
            text=row["text"],
            document_id=str(row["document_id"]),
            index=row["idx"]
        )

    # Documents

    def save_document(self, doc: Document) -> None:
        chunks_count = len(doc.chunks) if hasattr(doc, 'chunks') and isinstance(doc.chunks, list) else 0
        self._conn.execute(
            """
            INSERT INTO documents (id, path, name, chunks_count, checksum, ingested_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (checksum) DO NOTHING
            """,
            (
                doc.id,
                doc.path,
                doc.name,
                chunks_count,
                doc.checksum,
                doc.ingested_at,
            ),
        )
        self._conn.commit()

    def load_documents(self) -> dict[str, Document]:
        rows = self._conn.execute("SELECT * FROM documents").fetchall()
        return {
            str(row["id"]): Document.from_dict({
                "id": str(row["id"]),
                "path": row["path"],
                "name": row["name"],
                "chunks": [],
                "checksum": row["checksum"],
                "ingested_at": row["ingested_at"],
            })
            for row in rows
        }

    def get_document_by_checksum(self, checksum: str) -> Document | None:
        row = self._conn.execute(
            "SELECT * FROM documents WHERE checksum = %s", (checksum,)
        ).fetchone()
        if row is None:
            return None
        return Document.from_dict({
            "id": str(row["id"]),
            "path": row["path"],
            "name": row["name"],
            "chunks": [],
            "checksum": row["checksum"],
            "ingested_at": row["ingested_at"],
        })


    # Evidence

    def save_evidence(self, ev: EvidencePath) -> str:
        import json
        d = ev.to_dict()
        
        def to_clean_list(val) -> list:
            if not val:
                return []
            
            # 1. Unpack JSON strings if pre-serialized
            if isinstance(val, str):
                trimmed = val.strip()
                if trimmed.startswith("[") and trimmed.endswith("]"):
                    try:
                        val = json.loads(trimmed)
                    except json.JSONDecodeError:
                        pass

            # 2. Extract UUID strings from lists/tuples/sets
            if isinstance(val, (list, tuple, set)):
                cleaned = []
                for item in val:
                    if not item:
                        continue
                    # Handle raw strings or UUID objects
                    if isinstance(item, str):
                        cleaned.append(item)
                    # Handle dictionaries (like the Edge dict throwing the error)
                    elif isinstance(item, dict) and "id" in item:
                        cleaned.append(str(item["id"]))
                    # Handle objects with an id attribute (like model classes)
                    elif hasattr(item, "id"):
                        cleaned.append(str(item.id))
                    # Handle tuple pairs from vector scores (ID, score)
                    elif isinstance(item, (tuple, list)) and len(item) > 0:
                        sub_item = item[0]
                        if isinstance(sub_item, dict) and "id" in sub_item:
                            cleaned.append(str(sub_item["id"]))
                        elif hasattr(sub_item, "id"):
                            cleaned.append(str(sub_item.id))
                        else:
                            cleaned.append(str(sub_item))
                    else:
                        cleaned.append(str(item))
                return cleaned
                
            # 3. Fallback for single values
            if isinstance(val, dict) and "id" in val:
                return [str(val["id"])]
            if hasattr(val, "id"):
                return [str(val.id)]
            return [str(val)]

        self._conn.execute(
            """
            INSERT INTO evidence_paths
            (id, question, entry_nodes, visited_nodes, traversed_edges, source_chunks, answer, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                str(d["id"]),
                d["question"],
                to_clean_list(d.get("entry_nodes")),
                to_clean_list(d.get("visited_nodes")),
                to_clean_list(d.get("traversed_edges")),
                to_clean_list(d.get("source_chunks")),
                d.get("answer"),
                d.get("confidence"),
                d.get("created_at"),
            ),
        )
        self._conn.commit()
        return str(d["id"])

    def load_evidence_for_question(self, question: str, limit: int = 10) -> list[EvidencePath]:
        rows = self._conn.execute(
            """
            SELECT * FROM evidence_paths
            WHERE question = %s
            ORDER BY confidence DESC, created_at DESC
            LIMIT %s
            """,
            (question, limit),
        ).fetchall()
        return [self._row_to_evidence(row) for row in rows]

    def close(self) -> None:
        self._conn.close()

    # Helpers
    @staticmethod
    def _row_to_edge(row) -> Edge:
        return Edge.from_dict({
            "id": str(row["id"]),
            "source_id": str(row["source_id"]),
            "target_id": str(row["target_id"]),
            "relation": row["relation"],
            "source_chunk_id": str(row["source_chunk_id"]),
            "created_at": row["created_at"],
        })

    @staticmethod
    def _row_to_evidence(row) -> EvidencePath:
        return EvidencePath.from_dict({
            "id": str(row["id"]),
            "question": row["question"],
            "entry_nodes": [str(uid) for uid in row["entry_nodes"]],
            "visited_nodes": [str(uid) for uid in row["visited_nodes"]],
            "traversed_edges": [str(uid) for uid in row["traversed_edges"]],
            "source_chunks": [str(uid) for uid in row["source_chunks"]],"answer": row["answer"],"confidence": row["confidence"],"created_at": row["created_at"],
        })