import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Chunk:
    text: str
    source_doc: str
    index: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))