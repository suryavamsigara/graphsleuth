"""
Agent for GraphSleuth

ReAct style agent that answers questions by traversing the knowledge graph, reading source chunks, and synthesizing cited answers.
Returns both the answer and a complete ReasoningTrace for visualization.
"""
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from sklearn.metrics.pairwise import cosine_similarity

from engine.embeddings.encoder import EmbeddingEncoder
from engine.models.document import ReasoningTrace
from engine.graph.knowledge_graph import KnowledgeGraph
from engine.agent.prompts import REASONER_SYSTEM_PROMPT
from engine.client import get_openai, get_ollama


# -------------------------------------------------
# Agent result type
# -------------------------------------------------

@dataclass
class AgentAnswer:
    """Structured output from the investigator agent."""
    answer: str
    trace: ReasoningTrace
    reasoning_steps: list[dict]
    model_used: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    created_at: str = field(default_factory=lambda : datetime.now(timezone.utc).isoformat())


class GraphReasoner:
    """
    ReAct style agent for graph based question answering.
    
    Flow:
        1. Search graph for entry points (embedding similarity)
        2. Traverse graph to collect trace (BFS)
        3. Read source chunks
        4. Synthesize answer with citations
        5. Return AgentAnswer with full ReasoningTrace

    Args:
        kg: KnowledgeGraph (populated already)
        max_trace_chunks: Max chunks to feed to LLM
        max_depth: Default BFS depth for graph traversal
        top_k: Default number of entry nodes
    """
    def __init__(
        self,
        kg: KnowledgeGraph,
        encoder: EmbeddingEncoder,
        model_name: str = "qwen3.5:4b",
        use_openai: bool = False,
        max_trace_chunks: int = 8,
        max_depth: int = 2,
        top_k: int = 3,
    ):
        self.kg = kg
        self.encoder = encoder
        self.model_name = model_name
        self.use_openai = use_openai
        self.max_trace_chunks = max_trace_chunks
        self.max_depth = max_depth
        self.top_k = top_k

        self.client = get_openai() if use_openai else get_ollama()


    def answer(self, question: str) -> AgentAnswer:
        """
        Answers a question by investigating the knowledge graph.
        """
        import time
        start_time = time.time()

        steps = []

        # Step 1: Find entry points
        step1_start = time.time()
        entry_nodes = self.kg.get_top_k_nodes(query=question, k=self.top_k)
        steps.append({
            "step": 1,
            "action": "search_nodes",
            "input": question,
            "output": entry_nodes,
            "latency_ms": round((time.time() - step1_start) * 1000, 2),
        })

        if not entry_nodes:
            return AgentAnswer(
                answer="I could not find any relevant entities in the knowledge graph for this question. "
                       "Try ingesting documents related to this topic first.",
                trace=ReasoningTrace(
                    question=question,
                    entry_nodes=[],
                    visited_nodes=[],
                    traversed_edges=[],
                    source_chunks=[],
                    confidence=0.0,
                ),
                reasoning_steps=steps,
                model_used=self.model_name,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )

        # Step 2: Traverse graph
        step2_start = time.time()
        trace = self.kg.multi_hop_query(
            question=question,
            top_k=self.top_k,
            max_depth=self.max_depth,
            direction="both",
        )
        steps.append({
            "step": 2,
            "action": "traverse_graph",
            "input": f"entry_nodes={trace.entry_nodes}, max_depth={self.max_depth}",
            "output": {
                "visited_nodes": len(trace.visited_nodes),
                "traversed_edges": len(trace.traversed_edges),
                "source_chunks": len(trace.source_chunks),
            },
            "latency_ms": round((time.time() - step2_start) * 1000, 2),
        })

        if not trace.entry_nodes and not trace.source_chunks:
            return AgentAnswer(
                answer="I could not find any relevant entities or source text for this question. "
                       "Try rephrasing your question or ingesting documents related to this topic.",
                trace=trace,
                reasoning_steps=steps,
                model_used=self.model_name,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )

        # Step 3: Read source chunks
        step3_start = time.time()
        chunk_lookup = {}  # chunk_id -> text (for citation)
        chunk_scores = []

        query_emb = self.encoder.encode_single(question)

        for cid in trace.source_chunks:
            chunk = self.kg.get_chunk(cid)
            if chunk:
                chunk_emb = self.encoder.encode_single(chunk.text)

                score = float(cosine_similarity(
                    np.array(query_emb).reshape(1, -1),
                    np.array(chunk_emb).reshape(1, -1)
                )[0][0])
                chunk_scores.append((cid, chunk.text, score))
                chunk_lookup[cid] = chunk.text

        chunk_scores.sort(key=lambda x: x[2], reverse=True)
        top_chunks = [
            f"[CHUNK {c_data[0]}]:\n{c_data[1]}"
            for c_data in chunk_scores
        ][:self.max_trace_chunks]


        if not top_chunks:
            return AgentAnswer(
                answer="I found relevant entities in the graph but could not retrieve their source text. "
                        "The graph may be corrupted or the chunks were not properly stored.",
                trace=trace,
                reasoning_steps=steps,
                model_used=self.model_name,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )

        steps.append({
            "step": 3,
            "action": "read_chunks",
            "input": f"{len(trace.source_chunks)} chunks available, {len(top_chunks)} retrieved",
            "output": f"Retrieved {len(top_chunks)} chunks",
            "latency_ms": round((time.time() - step3_start) * 1000, 2),
        })

        # Step 4: Build context for LLM
        entity_context = []
        for nid in trace.visited_nodes[:15]:  # Cap to avoid token overflow
            node = self.kg.get_node(nid)
            if node:
                entity_context.append(
                    f"ENTITY: {node.name} [{node.node_type}]\n"
                    f"  Description: {node.description}\n"
                    f"  Source chunks: {node.source_chunk_ids}\n"
                )

        # Include traversed edges for structural context
        edge_context = []
        for edge in trace.traversed_edges[:10]:
            src = self.kg.get_node(edge.source_id)
            tgt = self.kg.get_node(edge.target_id)
            if src and tgt:
                edge_context.append(
                    f"RELATION: {src.name} --[{edge.relation}]--> {tgt.name}"
                )

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
        1. Answer the question using ONLY the trace above
        2. Cite specific entities and source chunks for key claims
        3. If trace is insufficient, say "Insufficient trace" and explain what's missing
        4. If trace is contradictory, present both sides
        5. Be concise (3-5 sentences for simple questions, longer for complex ones)
        
        Answer:"""

        # Step 5: Synthesize with LLM
        step5_start = time.time()
        messages = [
            {"role": "system", "content": REASONER_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]

        try:
            if self.use_openai:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=2048,
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=False,
                    temperature=0.2,
                    max_completion_tokens=2048,
                    extra_body={
                        "options": {
                            "num_ctx": 8192,
                            "num_thread": 4,
                        }
                    }
                )

            answer_text = response.choices[0].message.content.strip()
            tokens_used = response.usage.total_tokens if response.usage else 0
        
        except Exception as e:
            answer_text = f"Error during synthesis: {e}"
            tokens_used = 0

        steps.append({
            "step": 5,
            "action": "synthesize",
            "input": f"{len(entity_context)} entities, {len(top_chunks)} chunks",
            "output": answer_text[:200] + "..." if len(answer_text) > 200 else answer_text,
            "latency_ms": round((time.time() - step5_start) * 1000, 2),
        })

        # Step 6: Save trace
        trace.answer = answer_text
        trace_id = self.kg.save_trace(trace)

        total_latency = round((time.time() - start_time) * 1000, 2)

        steps.append({
            "step": 6,
            "action": "save_trace",
            "input": trace_id,
            "output": "Reasoning trace persisted",
            "latency_ms": 0,
        })

        return AgentAnswer(
            answer=answer_text,
            trace=trace,
            reasoning_steps=steps,
            model_used=self.model_name,
            tokens_used=tokens_used,
            latency_ms=total_latency,
        )

    def explain_path(self, trace: ReasoningTrace) -> str:
        """
        Explanation of how the agent reached its answer.
        """
        lines = [f"Question: {trace.question}", ""]
        lines.append(f"Entry Points ({len(trace.entry_nodes)}):")
        for nid in trace.entry_nodes:
            node = self.kg.get_node(nid)
            if node:
                lines.append(f"  → {node.name} [{node.node_type}] (score: found via embedding search)")

        lines.append("")
        lines.append(f"Traversal Path ({len(trace.traversed_edges)} edges):")
        for edge in trace.traversed_edges:
            src = self.kg.get_node(edge.source_id)
            tgt = self.kg.get_node(edge.target_id)
            if src and tgt:
                lines.append(f"  {src.name} --[{edge.relation}]--> {tgt.name}")

        lines.append("")
        lines.append(f"Source Trace ({len(trace.source_chunks)} chunks):")
        for cid in trace.source_chunks[:5]:
            chunk = self.kg.get_chunk(cid)
            if chunk:
                preview = chunk.text[:100].replace("\n", " ")
                lines.append(f"  [{cid[:8]}...] {preview}...")

        lines.append("")
        lines.append(f"Confidence: {trace.confidence}")
        return "\n".join(lines)