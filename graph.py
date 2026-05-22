import uuid
from collections import defaultdict
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Node:
    name: str
    node_type: str
    source_doc: str
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass(frozen=True)
class Edge:
    source_id: str
    target_id: str
    relation: str
    source_doc: str

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
            print(f"  Content: {node.content[:80]}")
            print()
        
        print("\n" + "=" * 50)
        print(f"Total nodes: {len(self.nodes)}")
        print(f"Total edges: {sum(len(v) for v in self.edges.values())}")
        print("=" * 50)
        
graph = KnowledgeGraph()
node1 = Node(
    name="Node 1",
    node_type="Test",
    source_doc="test doc",
    content="This is first node i created"
)

node2 = Node(
    name="Node 2",
    node_type="Test 2",
    source_doc="test doc",
    content="This is seocond node"
)

edge1 = Edge(
    source_id=node1.id,
    target_id=node2.id,
    relation="just test",
    source_doc="test doc"
)

graph.add_node(node1)
graph.add_node(node2)
graph.create_edge(edge1)

graph.print_graph()