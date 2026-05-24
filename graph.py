"""
Chunk <-> Node - One Node can have manu source chunks (many-to-many)
later in sqlite, a junction table holds chunk ids and Node.
"""

import uuid
import numpy as np
from collections import deque
from typing import Optional
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from model2vec import StaticModel

from models import Chunk

@dataclass
class Node:
    node_type: str
    aliases: list[str]
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
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

class KnowledgeGraph:
    def __init__(self, embedding_model: StaticModel, querying_model: StaticModel):
        self.threshold = 0.85

        self.nodes: dict[str, Node] = {}
        self.edges: set[Edge] = set()

        self.chunks_list: dict[str, Chunk] = {}
        # self.documents: dict[str, Document] = {} # doc_id -> Document
        # self.chunk_to_doc: dict[str, str] = {} # chunk_id -> doc_id

        # Matrix for node matching during insertion
        self.embedding_matrix: np.ndarray | None = None
        self.embedding_ids: list[str] = []
        self.embedding_model = embedding_model

        # Matrix for query matching
        self.querying_matrix: np.ndarray | None = None
        self.querying_model = querying_model
    
    def add_node(self, node: Node):
        new_embedding = self.embedding_model.encode(node.name)
        reshaped_embedding = new_embedding.reshape(1, -1)

        new_querying_embedding = self.querying_model.encode(node.name).reshape(1, -1)

        if self.embedding_matrix is not None and len(self.embedding_matrix) > 0:
            similarities = cosine_similarity(reshaped_embedding, self.embedding_matrix)
            max_sim = similarities.max()

            if max_sim > self.threshold:
                max_idx = similarities.argmax()
                existing_id = self.embedding_ids[max_idx]
                existing_node = self.nodes[existing_id]

                existing_node.aliases.append(node.name)
                existing_node.source_chunk_ids.append(node.source_chunk_ids[0])
                return existing_id
            
        self.nodes[node.id] = node

        # Update embedding matrix

        if self.embedding_matrix is None:
            self.embedding_matrix = reshaped_embedding
            self.querying_matrix = new_querying_embedding
        else:
            self.embedding_matrix = np.vstack((self.embedding_matrix, reshaped_embedding))
            self.querying_matrix = np.vstack((self.querying_matrix, new_querying_embedding))
        
        self.embedding_ids.append(node.id)
        return node.id
    
    def create_edge(self, edge: Edge):
        self.edges.add(edge)

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

            for edge in self.edges:
                neighbor_id = None
                if edge.source_id == node_id:
                    neighbor_id = edge.target_id
                elif edge.target_id == node_id:
                    neighbor_id = edge.source_id
                
                if neighbor_id and neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, curr_depth + 1))
                
        source_chunk_ids = set()

        for node_id in visited:
            source_chunk_ids.update(self.nodes[node_id].source_chunk_ids)

        chunk_texts = [self.chunks_list[cid].text for cid in source_chunk_ids if cid in self.chunks_list]
        
        return chunk_texts

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
        print(f"Total edges: {len(self.edges)}")
        print("=" * 50)

