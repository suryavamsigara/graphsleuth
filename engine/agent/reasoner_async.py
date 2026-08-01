import asyncio
import time
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sklearn.metrics.pairwise import cosine_similarity

from engine.client_async import get_async_openai_client, get_async_ollama_client
from engine.embeddings.encoder import EmbeddingEncoder
from engine.models.document import EvidencePath
from engine.graph.knowledge_graph import KnowledgeGraph
from engine.agent.prompts import REASONER_SYSTEM_PROMPT


@dataclass
class AgentAnswer:
    answer: str
    evidence: EvidencePath
    reasoning_steps: list[dict]
    model_used: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _compute_confidence(entry_scores: list[float], chunk_scores: list[float]) -> float:
    """
    Confidence is derived from how strongly retrieval actually
    matched the question:

      60% weight: mean similarity of the entry nodes the search step found
      40% weight: mean similarity of the source chunks that were kept

    Either half missing degrades gracefully rather than dividing by zero.
    Clamped to [0, 1].
    """
    entry_avg = sum(entry_scores) / len(entry_scores) if entry_scores else 0.0
    chunk_avg = sum(chunk_scores) / len(chunk_scores) if chunk_scores else 0.0

    if entry_scores and chunk_scores:
        confidence = 0.6 * entry_avg + 0.4 * chunk_avg
    elif entry_scores:
        confidence = entry_avg
    elif chunk_scores:
        confidence = chunk_avg
    else:
        confidence = 0.0

    return max(0.0, min(1.0, confidence))


class AsyncGraphReasoner:
    def __init__(
        self,
        kg: KnowledgeGraph,
        encoder: EmbeddingEncoder,
        model_name: str = "qwen3.5:4b",
        use_openai: bool = False,
        max_evidence_chunks: int = 8,
        max_depth: int = 2,
        top_k: int = 3,
    ):
        self.kg = kg
        self.encoder = encoder
        self.model_name = model_name
        self.use_openai = use_openai
        self.max_evidence_chunks = max_evidence_chunks
        self.max_depth = max_depth
        self.top_k = top_k
        self.client = get_async_openai_client() if use_openai else get_async_ollama_client()

    async def answer_stream(
        self,
        question: str,
        confidence_threshold: float | None = None,
        top_k: int | None = None,
        max_depth: int | None = None,
    ):
        """Yields SSE-style dict events: step, evidence, token, done.

        `confidence_threshold` (0-1, from the chat panel's "confidence
        threshold" dropdown) is passed straight through to
        KnowledgeGraph.multi_hop_query's `min_score` override, tightening
        or loosening which neighbors the traversal keeps at each hop for
        just this question.

        `top_k` / `max_depth`, when given, override the constructor
        defaults for just this call.
        """
        resolved_top_k = top_k if top_k is not None else self.top_k
        resolved_max_depth = max_depth if max_depth is not None else self.max_depth

        start_time = time.time()
        steps = []

        # Step 1: entry nodes
        t0 = time.time()
        entry_nodes = await asyncio.to_thread(self.kg.get_top_k_nodes, question, resolved_top_k)
        steps.append({
            "step": 1,
            "action": "search_nodes",
            "input": question,
            "output": entry_nodes,
            "latency_ms": round((time.time() - t0) * 1000, 2),
        })
        yield {"type": "step", **steps[-1]}

        if not entry_nodes:
            yield {"type": "error", "message": "No relevant entities found"}
            return

        entry_scores = [score for _, score in entry_nodes]

        # Step 2: traverse
        t0 = time.time()
        evidence = await asyncio.to_thread(
            self.kg.multi_hop_query, question, resolved_top_k, resolved_max_depth, "both", confidence_threshold
        )
        steps.append({
            "step": 2,
            "action": "traverse_graph",
            "input": {"entry_nodes": evidence.entry_nodes, "max_depth": resolved_max_depth},
            "output": {
                "visited_nodes": len(evidence.visited_nodes),
                "traversed_edges": len(evidence.traversed_edges),
                "source_chunks": len(evidence.source_chunks),
            },
            "latency_ms": round((time.time() - t0) * 1000, 2),
        })
        yield {"type": "step", **steps[-1]}
        yield {"type": "evidence", "data": evidence.to_dict()}

        # Step 3: read & score chunks
        t0 = time.time()
        chunk_lookup: dict[str, str] = {}
        chunk_scores: list[tuple[str, str, float]] = []
        query_emb = await asyncio.to_thread(self.encoder.encode_single, question)

        for cid in evidence.source_chunks:
            chunk = await asyncio.to_thread(self.kg.get_chunk, cid)
            if not chunk:
                continue
            chunk_emb = await asyncio.to_thread(self.encoder.encode_single, chunk.text)
            score = float(cosine_similarity(
                np.array(query_emb).reshape(1, -1),
                np.array(chunk_emb).reshape(1, -1),
            )[0][0])
            chunk_scores.append((cid, chunk.text, score))
            chunk_lookup[cid] = chunk.text

        chunk_scores.sort(key=lambda x: x[2], reverse=True)
        top_chunks_with_scores = chunk_scores[: self.max_evidence_chunks]
        top_chunks = [f"[CHUNK {c[0]}]:\n{c[1]}" for c in top_chunks_with_scores]

        steps.append({
            "step": 3,
            "action": "read_chunks",
            "input": f"{len(evidence.source_chunks)} chunks available",
            "output": f"Retrieved {len(top_chunks)} chunks",
            "latency_ms": round((time.time() - t0) * 1000, 2),
        })
        yield {"type": "step", **steps[-1]}

        if not top_chunks:
            yield {"type": "error", "message": "Found entities but could not retrieve source text"}
            return

        confidence = _compute_confidence(entry_scores, [s for _, _, s in top_chunks_with_scores])

        # Step 4: build context
        entity_context = []
        for nid in evidence.visited_nodes[:15]:
            node = await asyncio.to_thread(self.kg.get_node, nid)
            if node:
                entity_context.append(
                    f"ENTITY: {node.name} [{node.node_type}]\n  Description: {node.description}"
                )

        edge_context = []
        for edge in evidence.traversed_edges[:10]:
            src = await asyncio.to_thread(self.kg.get_node, edge.source_id)
            tgt = await asyncio.to_thread(self.kg.get_node, edge.target_id)
            if src and tgt:
                edge_context.append(f"RELATION: {src.name} --[{edge.relation}]--> {tgt.name}")

        context = f"""=== KNOWLEDGE GRAPH EVIDENCE ===
        ENTITIES DISCOVERED ({len(entity_context)}):
        {chr(10).join(entity_context)}

        RELATIONS DISCOVERED ({len(edge_context)}):
        {chr(10).join(edge_context)}

        SOURCE CHUNKS ({len(top_chunks)}):
        {chr(10).join(top_chunks)}

        === QUESTION ===
        {question}

        === INSTRUCTIONS ===
        1. Answer using ONLY the evidence above.
        2. Cite specific entities and source chunks.
        3. If insufficient, say "Insufficient evidence" and explain why.
        4. Be concise (3-5 sentences) unless the question is complex.

        Answer:
        """

        # Step 5: stream synthesis
        t0 = time.time()
        messages = [
            {"role": "system", "content": REASONER_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
            max_tokens=2048,
            stream=True,
            stream_options={"include_usage": True},
        )

        answer_text = ""
        tokens_used = 0
        async for chunk in response:
            delta = chunk.choices[0].delta.content or ""
            answer_text += delta
            if chunk.usage:
                tokens_used = chunk.usage.total_tokens
            if delta:
                yield {"type": "token", "token": delta}

        steps.append({
            "step": 5,
            "action": "synthesize",
            "input": f"{len(entity_context)} entities, {len(top_chunks)} chunks",
            "output": answer_text[:200] + "..." if len(answer_text) > 200 else answer_text,
            "latency_ms": round((time.time() - t0) * 1000, 2),
        })
        yield {"type": "step", **steps[-1]}

        # Step 6: persist
        evidence.answer = answer_text
        evidence.confidence = confidence
        evidence_id = await asyncio.to_thread(self.kg.save_evidence, evidence)

        total_latency = round((time.time() - start_time) * 1000, 2)
        steps.append({
            "step": 6,
            "action": "save_evidence",
            "input": evidence_id,
            "output": "Evidence path persisted",
            "latency_ms": 0,
        })
        yield {"type": "step", **steps[-1]}

        yield {
            "type": "done",
            "answer": answer_text,
            "evidence_id": evidence_id,
            "tokens_used": tokens_used,
            "latency_ms": total_latency,
            "confidence": confidence,
            "steps": steps,
        }