import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

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