"""
Chunk <-> Node - One Node can have manu source chunks (many-to-many)
later in sqlite, a junction table holds chunk ids and Node.
"""

import uuid
import numpy as np
from collections import defaultdict
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from model2vec import StaticModel

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
    def __init__(self, embedding_model: StaticModel):
        self.threshold = 0.85

        self.nodes: dict[str, Node] = {}
        self.edges: set[Edge] = set()

        # self.documents: dict[str, Document] = {} # doc_id -> Document
        # self.chunk_to_doc: dict[str, str] = {} # chunk_id -> doc_id

        self.embedding_matrix: np.ndarray | None = None
        self.embedding_ids: list[str] = []
        self.embedding_model = embedding_model
    
    def add_node(self, node: Node):
        new_embedding = self.embedding_model.encode(node.name)
        reshaped_embedding = new_embedding.reshape(1, -1)

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
        else:
            self.embedding_matrix = np.vstack((self.embedding_matrix, reshaped_embedding))
        
        self.embedding_ids.append(node.id)
        return node.id
    
    def create_edge(self, edge: Edge):
        self.edges.add(edge)
    
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

