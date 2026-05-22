import uuid
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Node:
    node_type: str
    aliases: list[str]
    source_chunk_id: str
    # content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def name(self):
        return self.aliases[0] if self.aliases else "UNKNOWN"


@dataclass(frozen=True)
class Edge:
    source_id: str
    target_id: str
    relation: str
    source_chunk_id: str

class KnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: dict[str, list[str]] = defaultdict(list)
    
    def add_node(self, node: Node):
        self.nodes[node.id] = node
    
    def create_edge(self, edge: Edge):
        if edge.source_id not in self.edges:
            self.edges[edge.source_id] = []
        self.edges[edge.source_id].append(edge.target_id)
    
    def print_graph(self):
        print("=" * 50)
        print("KNOWLEDGE GRAPH")
        print("=" * 50)
        
        print("\n--- NODES ---")
        for node_id, node in self.nodes.items():
            print(f"[{node_id[:8]}...] {node.name} ({node.node_type})")
            print(f"  Source: {node.source_doc}")
            print()
        
        print("\n" + "=" * 50)
        print(f"Total nodes: {len(self.nodes)}")
        print(f"Total edges: {sum(len(v) for v in self.edges.values())}")
        print("=" * 50)

