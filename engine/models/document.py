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
            "traversed_edges": json.dumps([e.to_dict() for e in self.traversed_edges]),
            "source_chunks": json.dumps(self.source_chunks),
            "answer": self.answer,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }