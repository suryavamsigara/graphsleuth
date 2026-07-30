from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    top_k: int = 3
    max_depth: int = 2

class QueryResponse(BaseModel):
    answer: str
    evidence_id: str | None = None
    latency_ms: float