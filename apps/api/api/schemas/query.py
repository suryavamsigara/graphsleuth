from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=3, ge=1, le=20)
    max_depth: int = Field(default=2, ge=1, le=5)
    # Passed to KnowledgeGraph.multi_hop_query as `min_score`
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

