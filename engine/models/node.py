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
    # Set by KnowledgeGraph.add_node() right before persisting, not by
    # EntityExtractor — that file constructs Node(...) with no project_id
    # argument, so this stays optional-with-default rather than required.
    project_id: str | None = None

    @property
    def name(self):
        return self.aliases[0] if self.aliases else "UNKNOWN"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "aliases": self.aliases,
            "description": self.description,
            "source_chunk_ids": self.source_chunk_ids,
            "created_at": self.created_at,
            "project_id": self.project_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Node":
        aliases = d["aliases"]
        if isinstance(aliases, str):
            aliases = json.loads(aliases)

        source_chunk_ids = d["source_chunk_ids"]
        if isinstance(source_chunk_ids, str):
            source_chunk_ids = json.loads(source_chunk_ids)

        return cls(
            id=d["id"],
            node_type=d["node_type"],
            aliases=aliases,
            description=d["description"],
            source_chunk_ids=source_chunk_ids,
            created_at=d["created_at"],
            project_id=d.get("project_id"),
        )