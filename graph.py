"""
Chunk <-> Node - One Node can have manu source chunks (many-to-many)
later in sqlite, a junction table holds chunk ids and Node.
"""

import uuid
import json
import hashlib
import sqlite3
import numpy as np
from pathlib import Path
from datetime import datetime, timezone
from collections import deque, defaultdict
from typing import Optional, Iterator
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from model2vec import StaticModel


@dataclass
class Chunk:
    """A text chunk extracted from a document."""
    id: str
    text: str
    document_id: str
    index: int = 0 # position within the document

@dataclass
class Node:
    "A knowledge graph entity."
    node_type: str
    aliases: list[str]
    description: str
    source_chunk_ids: list[str] # many-to-many
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def name(self):
        return self.aliases[0] if self.aliases else "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "aliases": json.dumps(self.aliases),
            "description": self.description,
            "source_chunk_ids": json.dumps(self.source_chunk_ids),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        return cls(
            id=d["id"],
            node_type=d["node_type"],
            aliases=json.loads(d["aliases"]),
            description=d["description"],
            source_chunk_ids=json.loads(d["source_chunk_ids"]),
            created_at=d["created_at"],
        )


@dataclass(unsafe_hash=True)
class Edge:
    """A directed relationship between two nodes."""
    source_id: str
    target_id: str
    relation: str
    source_chunk_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "source_chunk_id": self.source_chunk_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(
            id=d["id"],
            source_id=d["source_id"],
            target_id=d["target_id"],
            relation=d["relation"],
            source_chunk_id=d["source_chunk_id"],
            created_at=d["created_at"]
        )

@dataclass
class Document:
    """A source document that was ingested into the graph."""
    path: str
    name: str
    chunks: list[str] # List of chunk IDs
    checksum: str
    ingested_at: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "chunks": json.dumps(self.chunks),
            "checksum": self.checksum,
            "ingested_at": self.ingested_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        return cls(
            id=d["id"],
            path=d["path"],
            name=d["name"],
            chunks=json.loads(d["chunks"]),
            checksum=d["checksum"],
            ingested_at=d["ingested_at"],
        )



class GraphStore:
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        node_type TEXT NOT NULL,
        aliases TEXT NOT NULL,          -- JSON array
        description TEXT,
        source_chunk_ids TEXT NOT NULL, -- JSON array
        created_at TEXT
    );

    CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            source_chunk_id TEXT NOT NULL,
            created_at TEXT,
            UNIQUE(source_id, target_id, relation, source_chunk_id)
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        text TEXT NOT NULL,
        document_id TEXT NOT NULL,
        idx INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        path TEXT NOT NULL,
        name TEXT NOT NULL,
        chunks TEXT NOT NULL,           -- JSON array of chunk IDs
        checksum TEXT UNIQUE NOT NULL,
        ingested_at TEXT
    );
    

    CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
    CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
    CREATE INDEX IF NOT EXISTS idx_edges_relation ON edges(relation);
    CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);
    """

    def __init__(self, db_path: str = "graphsleuth.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript(self.SCHEMA)
        self._conn.commit()

    def save_node(self, node: Node) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO nodes
            (id, node_type, aliases, description, source_chunk_ids, created_at)
            VALUES (:id, :node_type, :aliases, :description, :source_chunk_ids, :created_at)""",
            node.to_dict(),
        )
        self._conn.commit()

    def load_nodes(self) -> dict[str, Node]:
        rows = self._conn.execute("SELECT * FROM nodes").fetchall()
        return {row["id"]: Node.from_dict(dict(row)) for row in rows}

    def delete_node(self, node_id: str) -> bool:
        self._conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        self._conn.execute("DELETE FROM edges WHERE source_id = ? OR target_id = ?", (node_id, node_id))
        self._conn.commit()

    def save_edge(self, edge: Edge) -> bool:
        """Returns True if inserted, False if duplicate."""
        try:
            self._conn.execute(
                """INSERT INTO edges
                (id, source_id, target_id, relation, source_chunk_id, created_at)
                VALUES (:id, :source_id, :target_id, :relation, :source_chunk_id, :created_at)""",
                edge.to_dict(),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def load_edges(self) -> list[Edge]:
        rows = self._conn.execute("SELECT * FROM edges").fetchall()
        return [Edge.from_dict(dict(row)) for row in rows]

    def save_chunk(self, chunk: Chunk) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO chunks (id, text, document_id, idx)
            VALUES (?, ?, ?, ?)""",
            (chunk.id, chunk.text, chunk.document_id, chunk.index),
        )
        self._conn.commit()

    def load_chunk(self) -> dict[str, Chunk]:
        rows = self._conn.execute("SELECT * FROM chunks").fetchall()
        return {
            row["id"]: Chunk(
                id=row["id"],
                text=row["text"],
                document_id=row["document_id"],
                index=row["idx"],
            )
            for row in rows
        }

    def get_chunk(self, chunk_id) -> Optional[Chunk]:
        row = self._conn.execute(
            "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        if row is None:
            return None
        return Chunk(
            id = row["id"],
            text=row["text"],
            document_id=row["document_id"],
            index=row["idx"],
        )


    def save_document(self, doc: Document) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO documents
            (id, path, name, chunks, checksum, ingested_at)
            VALUES (:id, :path, :name, :chunks, :checksum, :ingested_at)
            """,
            doc.to_dict()
        )
        self._conn.commit()

    def load_documents(self) -> dict[str, Document]:
        rows = self._conn.execute("SELECT * FROM DOCUMENTS").fetchall()
        return {row["id"]: Document.from_dict(dict(row)) for row in rows}

    def close(self):
        self._conn.close()



class KnowledgeGraph:
    def __init__(self, embedding_model: StaticModel, querying_model: StaticModel):
        self.threshold = 0.85

        self.nodes: dict[str, Node] = {}
        self.adj_list: dict[str, list[Edge]] = defaultdict(list)
        self.chunks_list: dict[str, Chunk] = {}

        self.documents: dict[str, Document] = {} # doc_id -> Document
        self.doc_checksums: set[str] = set() # Set of processed SHA-256 strings

        # Matrix for node matching during insertion
        self.embedding_matrix: np.ndarray | None = None
        self.embedding_ids: list[str] = []
        self.embedding_model = embedding_model

        # Matrix for query matching
        self.querying_matrix: np.ndarray | None = None
        self.querying_model = querying_model

    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """
        Reads a file in binary chunks and computes its unique SHA-256 hash.
        Reads in chunks ensuring large files don't crash system memory.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not calculate checksum. File missing: {file_path}")
    
    def register_document(self, file_path: str, file_name: str, chunk_ids: list[str]) -> str | None:
        """
        Calculates file checksum, verifies duplicates, and registers the doc.
        """
        checksum = KnowledgeGraph.calculate_checksum(file_path)

        if checksum in self.doc_checksums:
            print(f"Skipping ingestion: Document '{file_name}' already exists.")
            return None
        
        new_doc = Document(
            path=file_path,
            name=file_name,
            chunks=chunk_ids,
            checksum=checksum,
            ingested_at=datetime.now(timezone.utc).isoformat()
        )

        self.documents[new_doc.id] = new_doc
        self.doc_checksums.add(checksum)
        
        return new_doc.id

    def add_node(self, node: Node) -> str:
        """
        Accepts the heavily validated node from ingestion.
        Embeds only the canonical name for future user search queries.
        """
        self.nodes[node.id] = node

        # Embed for graph retrieval
        search_text = f"{node.name} {node.description}".strip()
        new_querying_embedding = self.querying_model.encode(search_text).reshape(1, -1)

        if self.querying_matrix is None:
            self.querying_matrix = new_querying_embedding
        else:
            self.querying_matrix = np.vstack((self.querying_matrix, new_querying_embedding))
        
        self.embedding_ids.append(node.id)
        return node.id
    
    def create_edge(self, edge: Edge):
        """
        Stores edges in an adjacency list for O(1) node connection lookups.
        """
        self.adj_list[edge.source_id].append(edge)
        self.adj_list[edge.target_id].append(edge)

    def add_chunk(self, chunk: Chunk):
        """
        Stores chunk by ID
        """
        self.chunks_list[chunk.id] = chunk
        return chunk.id
    
    def get_chunks(self):
        return self.chunks_list
    
    def get_chunk(self, chunk_id: str):
        return
    
    def _get_top_k_nodes(self, question: str, k: int = 5) -> list[str]:
        """Helper method to find initial entry points in the graph."""
        if self.querying_matrix is None or len(self.querying_matrix) == 0:
            return []
        
        query_embedding = self.querying_model.encode(question)
        reshaped_query_embd = query_embedding.reshape(1, -1)

        # Do cosine search and get top K most relevant nodes
        cos_search = cosine_similarity(reshaped_query_embd, self.querying_matrix) # (1, n)
        
        actual_k = min(k, len(self.embedding_ids))
        top_k_indices = cos_search[0].argsort()[::-1][:actual_k]
        return [self.embedding_ids[idx] for idx in top_k_indices]
    
    def query(
        self,
        question: str,
        top_k: int = 5,
        max_depth: int = 2,
        score_threshold: Optional[float] = None
    ) -> list[str]:
        """
        Embeds the question, cosine search,
        fetches connected neighbours via BFS,
        collects all source chunks from those nodes,
        returns the chunks / passes to LLM with q
        """
        top_node_ids = self._get_top_k_nodes(question, top_k)

        visited = set(top_node_ids)
        queue = deque((node_id, 0) for node_id in top_node_ids)

        while queue:
            node_id, curr_depth = queue.popleft()

            if curr_depth >= max_depth:
                continue

            for edge in self.adj_list[node_id]:
                neighbor_id = None
                if edge.source_id == node_id:
                    neighbor_id = edge.target_id
                else:
                    neighbor_id = edge.source_id
                
                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))
                
        source_chunk_ids = set()

        for node_id in visited:
            source_chunk_ids.update(self.nodes[node_id].source_chunk_ids)

        chunk_texts = [self.chunks_list[cid].text for cid in source_chunk_ids if cid in self.chunks_list]
        
        return chunk_texts
    
    def get_neighborhood(self, node_id: str, depth: int = 2) -> list[Node]:
        visited = {node_id}
        queue = deque((node_id, 0))

        while queue:
            n_id, curr_depth = queue.popleft()

            if curr_depth >= depth:
                continue

            for edge in self.adj_list[node_id]:
                neighbor_id = None
                if edge.source_id == n_id:
                    neighbor_id = edge.target_id
                else:
                    neighbor_id = edge.source_id
                
                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))
        
        return [self.nodes[n_id] for n_id in visited]

    def traverse(self, question: str):
        top_node_id = self._get_top_k_nodes(question, 1)

        visited = set(top_node_id)
        queue = deque((top_node_id, 0))

        while queue:
            node_id, curr_depth = queue.popleft()
            desc_list = [] # [(node_id, description)]

            for edge in self.adj_list[node_id]:
                neighbour_id = None
                
                if edge.source_id == node_id:
                    neighbour_id == edge.target_id

                    desc_list.append((neighbour_id, self.nodes[neighbour_id].description))
            
            # take embeddings of description, query with them, and pick only one, add it to the queue
            embeds = []
            
        
        
    def _get_total_edges_count(self) -> int:
        total_entries = sum(len(edges) for edges in self.adj_list.values())
        return total_entries // 2

    def print_graph(self):
        print("=" * 50)
        print("KNOWLEDGE GRAPH")
        print("=" * 50)
        
        print("\n--- NODES ---")
        for node_id, node in self.nodes.items():
            print(f"[{node_id[:8]}...] {node.name} ({node.node_type})")
            print(f"  Source: {node.source_chunk_ids}")
            print()
        
        print("\n" + "=" * 50)
        print(f"Total nodes: {len(self.nodes)}")
        print(f"Total edges: {self._get_total_edges_count()}")
        print("=" * 50)





from datetime import datetime, timezone
from model2vec import StaticModel

from graph import GraphStore, Node, Edge, Chunk, Document


def main():
    store = GraphStore("test_graph.db")

    chunk = Chunk(
        id="chunk1",
        text="Python was created by Guido van Rossum.",
        document_id="doc1",
        index=0,
    )

    store.save_chunk(chunk)

    loaded_chunk = store.get_chunk("chunk1")

    print("Chunk")
    print(loaded_chunk)
    print()

    node = Node(
        node_type="Person",
        aliases=["Guido van Rossum"],
        description="Creator of Python",
        source_chunk_ids=["chunk1"],
    )

    store.save_node(node)

    nodes = store.load_nodes()

    print("Nodes")
    for n in nodes.values():
        print(n)
    print()

    python = Node(
        node_type="Language",
        aliases=["Python"],
        description="Programming language",
        source_chunk_ids=["chunk1"],
    )

    store.save_node(python)

    edge = Edge(
        source_id=python.id,
        target_id=node.id,
        relation="created_by",
        source_chunk_id="chunk1",
    )

    inserted = store.save_edge(edge)
    print("Edge inserted:", inserted)

    edges = store.load_edges()

    print("\nEdges")
    for e in edges:
        print(e)
    print()

    doc = Document(
        path="sample.txt",
        name="sample.txt",
        chunks=["chunk1"],
        checksum="dummychecksum",
        ingested_at=datetime.now(timezone.utc).isoformat(),
    )

    store.save_document(doc)

    docs = store.load_documents()

    print("Documents")
    for d in docs.values():
        print(d)
    print()


    print("Deleting node:", node.aliases[0])

    store.delete_node(node.id)

    print("\nRemaining Nodes")
    for n in store.load_nodes().values():
        print(n)

    print("\nRemaining Edges")
    print(store.load_edges())

    store.close()


if __name__ == "__main__":
    main()