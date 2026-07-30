from fastapi import APIRouter
from pydantic import BaseModel

from apps.api.dependencies import get_agent

router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/")
def ask_question(req: QueryRequest):
    agent = get_agent()
    result = agent.answer(req.question)
    return {
        "answer": result.answer,
        "confidence": result.evidence.confidence,
        "visited_nodes": len(result.evidence.visited_nodes),
        "traversed_edges": len(result.evidence.traversed_edges),
        "source_chunks": len(result.evidence.source_chunks),
        "latency_ms": result.latency_ms,
    }