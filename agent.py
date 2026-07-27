from dataclasses import dataclass, field
from datetime import datetime, timezone

from graph import KnowledgeGraph, EvidencePath
from client import get_ollama, get_openai


@dataclass
class AgentAnswer:
    """Structured output from the investigator agent."""
    answer: str
    evidence: EvidencePath
    reasoning_steps: list[dict]
    model_used: str
    tokens_used: int = 0
    latency_ms: float = 0.0
    created_at: str = field(default_factory=lambda : datetime.now(timezone.utc).isoformat())


INVESTIGATOR_SYSTEM_PROMPT = """You are GraphSleuth Investigator — an analytical agent that answers questions by examining evidence from a knowledge graph.

You have access to:
1. A knowledge graph of entities (people, organizations, events, etc.) and their relationships
2. Source text chunks that ground every entity and relation in the original documents

Your task:
- Synthesize a clear, accurate answer based ONLY on the provided evidence
- Cite specific entities and source chunks in your answer
- If evidence is insufficient, say so explicitly — do not hallucinate
- If evidence is contradictory, present both sides and note the conflict

CITATION FORMAT:
- When referencing an entity, use its canonical name: [Entity Name]
- When referencing a source, use: [Source: chunk-id]
- For key claims, include both: "Sam Altman [PERSON] founded OpenAI [ORGANIZATION] [Source: abc-123]"

Be concise but thorough. Prioritize factual accuracy over completeness."""


class InvestigatorAgent:
    """
    ReAct style agent for graph based question answering
    """
    def __init__(
        self,
        kg: KnowledgeGraph,
        model_name: str = "qwen3.5:4b",
        use_openai: bool = False,
        max_evidence_chunks: int = 8,
        max_depth: int = 2,
        top_k: int = 3,
    ):
        self.kg = kg
        self.model_name = model_name
        self.use_openai = use_openai
        self.max_evidence_chunks = max_evidence_chunks
        self.max_depth = max_depth
        self.top_k = top_k

        self.client = get_openai() if use_openai else get_ollama()


    def investigate(self, question: str) -> AgentAnswer:
        """
        Answers a question by investigating the knowledge graph.
        """
        import time
        start_time = time.time()

        steps = []

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
                evidence=EvidencePath(
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
        evidence = self.kg.multi_hop_query(
            question=question,
            top_k=self.top_k,
            direction="both",
        )
        steps.append({
            "step": 2,
            "action": "traverse_graph",
            "input": f"entry_nodes={evidence.entry_nodes}, max_depth={self.max_depth}",
            "output": {
                "visited_nodes": len(evidence.visited_nodes),
                "traversed_edges": len(evidence.traversed_edges),
                "source_chunks": len(evidence.source_chunks),
            },
            "latency_ms": round((time.time() - step2_start) * 1000, 2),
        })

        # Step 3: Read source chunks
        step3_start = time.time()
        chunk_texts = []
        chunk_lookup = {}  # chunk_id -> text (for citation)

        for cid in evidence.source_chunks[:self.max_evidence_chunks]:
            chunk = self.kg.get_chunk(cid)
            if chunk:
                chunk_texts.append(f"[CHUNK {cid}]:\n{chunk.text}\n")
                chunk_lookup[cid] = chunk.text


        if not chunk_texts:
            return AgentAnswer(
                answer="I found relevant entities in the graph but could not retrieve their source text. "
                        "The graph may be corrupted or the chunks were not properly stored.",
                evidence=evidence,
                reasoning_steps=steps,
                model_used=self.model_name,
                latency_ms=round((time.time() - start_time) * 1000, 2),
            )

        steps.append({
            "step": 3,
            "action": "read_chunks",
            "input": f"{len(evidence.source_chunks)} chunks available, {len(chunk_texts)} retrieved",
            "output": f"Retrieved {len(chunk_texts)} chunks",
            "latency_ms": round((time.time() - step3_start) * 1000, 2),
        })

        # Step 4: Build context for LLM
        entity_context = []
        for nid in evidence.visited_nodes[:15]:  # Cap to avoid token overflow
            node = self.kg.get_node(nid)
            if node:
                entity_context.append(
                    f"ENTITY: {node.name} [{node.node_type}]\n"
                    f"  Description: {node.description}\n"
                    f"  Source chunks: {node.source_chunk_ids}\n"
                )

        # Include traversed edges for structural context
        edge_context = []
        for edge in evidence.traversed_edges[:10]:
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
        
        SOURCE CHUNKS ({len(chunk_texts)}):
        {chr(10).join(chunk_texts)}
        
        === QUESTION ===
        {question}
        
        === INSTRUCTIONS ===
        1. Answer the question using ONLY the evidence above
        2. Cite specific entities and source chunks for key claims
        3. If evidence is insufficient, say "Insufficient evidence" and explain what's missing
        4. If evidence is contradictory, present both sides
        5. Be concise (3-5 sentences for simple questions, longer for complex ones)
        
        Answer:"""

        # Step 5: Synthesize with LLM
        step5_start = time.time()
        messages = [
            {"role": "system", "content": INVESTIGATOR_SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ]

        try:
            if self.use_openai:
                response = self.client.chat.completions.create(
                    model="deepseek-v4-flash",
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
            "input": f"{len(entity_context)} entities, {len(chunk_texts)} chunks",
            "output": answer_text[:200] + "..." if len(answer_text) > 200 else answer_text,
            "latency_ms": round((time.time() - step5_start) * 1000, 2),
        })

        # Step 6: Save evidence
        evidence.answer = answer_text
        evidence_id = self.kg.save_evidence(evidence)

        total_latency = round((time.time() - start_time) * 1000, 2)

        steps.append({
            "step": 6,
            "action": "save_evidence",
            "input": evidence_id,
            "output": "Evidence path persisted",
            "latency_ms": 0,
        })

        return AgentAnswer(
            answer=answer_text,
            evidence=evidence,
            reasoning_steps=steps,
            model_used=self.model_name,
            tokens_used=tokens_used,
            latency_ms=total_latency,
        )

    def explain_path(self, evidence: EvidencePath) -> str:
        """
        Explanation of how the agent reached its answer.
        """
        lines = [f"Question: {evidence.question}", ""]
        lines.append(f"Entry Points ({len(evidence.entry_nodes)}):")
        for nid in evidence.entry_nodes:
            node = self.kg.get_node(nid)
            if node:
                lines.append(f"  → {node.name} [{node.node_type}] (score: found via embedding search)")

        lines.append("")
        lines.append(f"Traversal Path ({len(evidence.traversed_edges)} edges):")
        for edge in evidence.traversed_edges:
            src = self.kg.get_node(edge.source_id)
            tgt = self.kg.get_node(edge.target_id)
            if src and tgt:
                lines.append(f"  {src.name} --[{edge.relation}]--> {tgt.name}")

        lines.append("")
        lines.append(f"Source Evidence ({len(evidence.source_chunks)} chunks):")
        for cid in evidence.source_chunks[:5]:
            chunk = self.kg.get_chunk(cid)
            if chunk:
                preview = chunk.text[:100].replace("\n", " ")
                lines.append(f"  [{cid[:8]}...] {preview}...")

        lines.append("")
        lines.append(f"Confidence: {evidence.confidence}")
        return "\n".join(lines)


if __name__ == "__main__":
    from model2vec import StaticModel
    from graph import KnowledgeGraph
    from ingestion import IngestionPipeline

    # Setup
    embed = StaticModel.from_pretrained(
        "MinishLab/potion-retrieval-32M",
        dimensionality=128,
    )

    query = StaticModel.from_pretrained(
        "MinishLab/potion-retrieval-32M"
    )

    kg = KnowledgeGraph(embedding_model=embed, querying_model=query, db_path="test_graph.db")

    from extractor import EntityExtractor

    extractor = EntityExtractor(model_name="qwen3.5:4b", embedding_model=embed)
    pipeline = IngestionPipeline(kg=kg, extractor=extractor)


    result = pipeline.ingest_file("file.txt", "file")
    print(f"Ingested: {result['chunks_processed']} chunks, {result['nodes_created']} nodes, {result['edges_created']} edges")

    # Test agent
    agent = InvestigatorAgent(
        kg=kg,
        use_openai=True,
        max_evidence_chunks=12,
        top_k=5
    )

    print("\n" + "="*60)
    print("QUESTION: Who were the key founders of OpenAI and what were their backgrounds before joining the organization?")
    print("="*60)

    answer = agent.investigate("Which companies are competing in cloud AI?")
    print(f"\nAnswer:\n{answer.answer}")
    print(f"\nEvidence: {len(answer.evidence.visited_nodes)} nodes, {len(answer.evidence.traversed_edges)} edges")
    print(f"Confidence: {answer.evidence.confidence}")
    print(f"Latency: {answer.latency_ms}ms")

    print("\n--- Reasoning Steps ---")
    for step in answer.reasoning_steps:
        print(f"  Step {step['step']}: {step['action']} ({step['latency_ms']}ms)")

    print("\n--- Path Explanation ---")
    print(agent.explain_path(answer.evidence))