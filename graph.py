"""
Chunk <-> Node - One Node can have manu source chunks (many-to-many)
later in sqlite, a junction table holds chunk ids and Node.
"""

import uuid
import hashlib
import numpy as np
from datetime import datetime, timezone
from collections import deque, defaultdict
from typing import Optional
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from model2vec import StaticModel

from models import Chunk

@dataclass
class Node:
    node_type: str
    aliases: list[str]
    description: str
    source_chunk_ids: list[str] # many-to-many
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def name(self):
        return self.aliases[0] if self.aliases else "UNKNOWN"


@dataclass(unsafe_hash=True)
class Edge:
    source_id: str
    target_id: str
    relation: str
    source_chunk_id: str

@dataclass
class Document:
    path: str
    name: str
    chunks: list[str] # List of chunk IDs
    checksum: str
    ingested_at: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

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

