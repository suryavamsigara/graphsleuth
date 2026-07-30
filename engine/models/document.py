import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

from engine.models.edge import Edge

@dataclass
class Chunk:
    """A text chunk extracted from a document."""
    id: str
    text: str
    document_id: str
    index: int = 0 # position within the document


@dataclass
class Document:
    """A source document that was ingested into the graph."""
    path: str
    name: str
    checksum: str
    ingested_at: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "checksum": self.checksum,
            "ingested_at": self.ingested_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        return cls(
            id=d["id"],
            path=d["path"],
            name=d["name"],
            checksum=d["checksum"],
            ingested_at=d["ingested_at"],
        )


@dataclass
class EvidencePath:
    """
    A traceable path through the graph that an agent followed to answer a question.
    """
    question: str
    entry_nodes: list[str]
    visited_nodes: list[str]
    traversed_edges: list[Edge]
    source_chunks: list[str]
    answer: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "question": self.question,
            "entry_nodes": json.dumps(self.entry_nodes),
            "visited_nodes": json.dumps(self.visited_nodes),
            "traversed_edges": [e.to_dict() if hasattr(e, 'to_dict') else e for e in self.traversed_edges],
            "source_chunks": json.dumps(self.source_chunks),
            "answer": self.answer,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EvidencePath":
        # Safely re-instantiate your nested Edge objects from the JSON row data
        raw_edges = data.get("traversed_edges") or []
        
        edges = [
            Edge.from_dict(e) if isinstance(e, dict) else e 
            for e in raw_edges
        ]
        
        return cls(
            id=str(data["id"]),
            question=data["question"],
            entry_nodes=data.get("entry_nodes") or [],
            visited_nodes=data.get("visited_nodes") or [],
            traversed_edges=edges,
            source_chunks=data.get("source_chunks") or [],
            answer=data.get("answer", ""),
            confidence=float(data.get("confidence") or 0.0),
            created_at=str(data["created_at"]),
        )