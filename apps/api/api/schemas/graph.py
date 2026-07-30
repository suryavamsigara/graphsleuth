from pydantic import BaseModel


class TraverseRequest(BaseModel):
    start_node_id: str
    max_depth: int = 2
    direction: str = "both"

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    description: str
    is_entry: bool = False

class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    label: str
    source_name: str
    target_name: str

class EvidenceGraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]

class NodeSearchResponse(BaseModel):
    id: str
    name: str
    node_type: str
    score: float