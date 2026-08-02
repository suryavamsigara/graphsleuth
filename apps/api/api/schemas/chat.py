from pydantic import BaseModel


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    steps: list = []
    confidence: float | None = None
    latency_ms: float | None = None
    evidence_id: str | None = None
    created_at: str
