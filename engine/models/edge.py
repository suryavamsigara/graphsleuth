import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

@dataclass(unsafe_hash=True)
class Edge:
    """A directed relationship between two nodes."""
    source_id: str
    target_id: str
    relation: str
    source_chunk_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    # Set by KnowledgeGraph.create_edge() right before persisting.
    project_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": self.relation,
            "source_chunk_id": self.source_chunk_id,
            "created_at": self.created_at,
            "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Edge":
        return cls(
            id=d["id"],
            source_id=d["source_id"],
            target_id=d["target_id"],
            relation=d["relation"],
            source_chunk_id=d["source_chunk_id"],
            created_at=d["created_at"],
            project_id=d.get("project_id"),
        )