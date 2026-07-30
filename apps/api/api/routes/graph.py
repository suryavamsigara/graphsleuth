from fastapi import APIRouter, Depends, HTTPException

from apps.api.core.async_engine import AsyncEngine
from apps.api.dependencies import get_engine
from apps.api.api.schemas.graph import (
    TraverseRequest,
    EvidenceGraphResponse,
    GraphNode,
    GraphEdge,
    NodeSearchResponse,
)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.post("/traverse")
async def traverse_graph(
    req: TraverseRequest,
    engine: AsyncEngine = Depends(get_engine),
):
    visited, edges = await engine.traverse(
        req.start_node_id, req.max_depth, req.direction
    )
    return {
        "visited_nodes": list(visited),
        "edges": [e.to_dict() for e in edges],
    }


@router.get("/nodes/search")
async def search_nodes(
    q: str,
    k: int = 5,
    engine: AsyncEngine = Depends(get_engine),
):
    results = await engine.search_nodes(q, k)
    return [
        NodeSearchResponse(
            id=nid,
            name=(await engine.get_node(nid)).name if await engine.get_node(nid) else nid,
            node_type=(await engine.get_node(nid)).node_type if await engine.get_node(nid) else "UNKNOWN",
            score=round(score, 4),
        )
        for nid, score in results
    ]


@router.get("/nodes/{node_id}")
async def get_node(node_id: str, engine: AsyncEngine = Depends(get_engine)):
    node = await engine.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return {
        "id": node.id,
        "name": node.name,
        "node_type": node.node_type,
        "aliases": node.aliases,
        "description": node.description,
        "source_chunk_ids": node.source_chunk_ids,
    }


@router.get("/evidence/{evidence_id}")
async def get_evidence_graph(
    evidence_id: str,
    engine: AsyncEngine = Depends(get_engine),
):
    evidence = await engine.get_evidence_by_id(evidence_id)
    if not evidence:
        raise HTTPException(status_code=404, detail="Evidence not found")

    graph = await engine.get_evidence_graph(evidence)
    return EvidenceGraphResponse(
        nodes=[GraphNode(**n) for n in graph["nodes"]],
        edges=[GraphEdge(**e) for e in graph["edges"]],
    )


@router.get("/metrics")
async def graph_metrics(engine: AsyncEngine = Depends(get_engine)):
    return await engine.get_metrics()