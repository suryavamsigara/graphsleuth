"""
Entity & Relation extraction pipeline for GraphSleuth

Takes raw text chunks, calls a local LLM (Ollama), and returns structured
Node and Edge objects ready for ingestion into KnowledgeGraph.
"""

import json
import re
import httpx
import time
import numpy as np
from typing import Optional
from pydantic import BaseModel, Field
from sklearn.metrics.pairwise import cosine_similarity

from client import get_ollama, get_openai
from graph import Node, Edge

class ExtractedEntity(BaseModel):
    """Single entity as returned by the LLM."""
    name: str = Field(description="Canonical name of the entity. E.g. 'Elon Musk'")
    entity_type: str = Field(
        description="Category: PERSON, ORGANIZATION, LOCATION, EVENT, PRODUCT, CONCEPT, REGULATION, or OTHER"
    )
    description: str = Field(
        description="1-2 sentence description of this entity in context"
    )
    aliases: list[str] = Field(
        default_factory=list,
        description="Alternative names, abbreviations, or pronouns that refer to the same entity"
    )

class ExtractedRelation(BaseModel):
    """Single relation as returned by the LLM."""
    source: str = Field(description="Name of the source entity (must match an extracted entity name)")
    target: str = Field(description="Name of the target entity (must match an extracted entity name)")
    relation: str = Field(
        description="Short predicate. E.g. 'founded', 'acquired', 'caused', 'opposed', 'works_for'"
    )

class ExtractionResult(BaseModel):
    """Top-level schema we force the LLM to emit."""
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relations: list[ExtractedRelation] = Field(default_factory=list)

EXTRACTION_PROMPT = """
You are a precise knowledge-graph extraction engine.

TASK: Read the text below and extract:
1. ENTITIES — people, organizations, locations, events, products, concepts, regulations
2. RELATIONS — directed connections between those entities

RULES:
- Use canonical names (e.g. "Tesla, Inc." not "the company").
- Include 1-2 sentence descriptions grounded in the text. Descriptions should identify the entity itself.
Do not repeat relationship facts that are already represented as relations.
- Add aliases only if the text explicitly uses alternative names.
- Relations must use simple, exact predicates matching the schema
- Only extract entities and relations that are EXPLICITLY stated or strongly implied by the text. Do not hallucinate.
- If no entities or relations are present, return empty arrays.

OUTPUT FORMAT — strict JSON, no markdown, no commentary:
{
  "entities": [
    {
      "name": "...",
      "entity_type": "...",
      "description": "...",
      "aliases": ["..."]
    }
  ],
  "relations": [
    {
      "source": "...",
      "target": "...",
      "relation": "..."
    }
  ]
}

TEXT:
---
{chunk_text}
---
"""

class EntityExtractor:
    """
    Extracts Node and Edge objects from text chunks.
    """
    def __init__(
        self,
        model_name: str = "qwen3.5:4b",
        embedding_model=None,
        dedup_threshold: float = 0.85,
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: int = 120
    ):
        self.client = get_ollama()
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.dedup_threshold = dedup_threshold
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        self._node_embed_cache: dict[str, np.ndarray] = {}

    def extract(
        self,
        chunk_text: str,
        chunk_id: str,
        existing_nodes: Optional[dict[str, Node]] = None,
    ) -> tuple[list[Node], list[Edge]]:
        """Extracts nodes and edges from a single chunk."""
        print("Extracting...")
        raw_json = self._call_llm_with_retry(chunk_text)
        parsed = ExtractionResult.model_validate(raw_json)
        print("Extracted!")

        nodes: list[Node] = []
        name_to_node_id: dict[str, str] = {}

        for ent in parsed.entities:
            canonical_name = ent.name.strip()
            if not canonical_name:
                continue

            matched_node_id = self._find_duplicate(
                canonical_name, ent.description, existing_nodes
            )

            if matched_node_id:
                # Merge
                name_to_node_id[canonical_name] = matched_node_id

                for alias in ent.aliases:
                    name_to_node_id[alias.strip()] = matched_node_id
            else:
                # Create
                node = Node(
                    node_type=ent.entity_type.upper(),
                    aliases=[canonical_name] + [a.strip() for a in ent.aliases if a.strip()],
                    description=ent.description.strip(),
                    source_chunk_ids=[chunk_id],
                )
                nodes.append(node)
                name_to_node_id[canonical_name] = node.id
                for alias in ent.aliases:
                    name_to_node_id[alias.strip()] = node.id

        edges: list[Edge] = []
        for rel in parsed.relations:
            src_name = rel.source.strip()
            tgt_name = rel.target.strip()


            src_id = name_to_node_id.get(src_name)
            tgt_id = name_to_node_id.get(tgt_name)

            if src_id is None and existing_nodes:
                src_id = self._fuzzy_name_match(src_name, existing_nodes)
            if tgt_id is None and existing_nodes:
                tgt_id = self._fuzzy_name_match(tgt_name, existing_nodes)

            if src_id and tgt_id and src_id != tgt_id:
                edge = Edge(
                    source_id=src_id,
                    target_id=tgt_id,
                    relation=rel.relation.strip().lower().replace(" ", "_"),
                    source_chunk_id=chunk_id,
                )
                edges.append(edge)
        return nodes, edges


    def _call_llm_with_retry(self, chunk_text: str):
        prompt = EXTRACTION_PROMPT.replace("{chunk_text}", chunk_text.strip())
        print(chunk_text.strip())

        messages = [
        {"role": "system", "content": "You are a precise data extraction system. Always respond with raw JSON matching the expected format. CRUCIAL: Every entity must include the 'aliases' list field, even if it is empty []."},
        {"role": "user", "content": prompt}
    ]

        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    stream=False,
                    temperature=self.temperature,
                    max_completion_tokens=4096,
                    timeout=httpx.Timeout(self.timeout),
                    reasoning_effort="none",
                    extra_body={
                        "response_format": {
                            "type": "json_object",
                            "schema": ExtractionResult.model_json_schema()
                        },
                        "options": {
                            "num_ctx": 4096,
                            "temperature": 0.0,
                            "num_thread": 4,
                            "numa": True,
                            "low_vram": True,
                        }
                    }
                )

                response_text = response.choices[0].message.content
                print(response_text)
                return self._extract_json(response_text)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    time.sleep(1.5 * attempt)
                continue
        raise RuntimeError(
            f"LLM extraction failed after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _extract_json(self, text: str) -> dict:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    def _find_duplicate(
        self,
        name: str,
        description: str,
        existing_nodes: Optional[dict[str, Node]],
    ) -> Optional[str]:
        """
        Checks if name already exists in the graph.
        1. Exact alias match
        2. Partial/Substring name match
        3. Embedding cosine similarity
        """
        if not existing_nodes:
            return None

        name_lower = name.lower()
        name_tokens = set(name_lower.split())
        
        # Step 1: Exact alias match
        for node_id, node in existing_nodes.items():
            for alias in node.aliases:
                if alias.lower() == name_lower:
                    return node_id
        
        # Step 2: Partial/substring match
        # Check if the name is a substring of any existing alias, or vice versa
        for node_id, node in existing_nodes.items():
            for alias in node.aliases:
                alias_lower = alias.lower()
                alias_tokens = set(alias_lower.split())
                
                # Check if one is a substring of the other
                if name_lower in alias_lower or alias_lower in name_lower:
                    # Additional safeguard: check token overlap for multi-word names
                    if not name_tokens or not alias_tokens:
                        return node_id
                    # At least 50% token overlap
                    overlap = len(name_tokens & alias_tokens) / min(len(name_tokens), len(alias_tokens))
                    if overlap >= 0.5:
                        return node_id
        
        # Step 3: Embedding similarity
        if self.embedding_model is None:
            return None

        candidate_text = f"{name} {description}".strip()
        candidate_emb = self.embedding_model.encode(candidate_text).reshape(1, -1)

        ids = []
        embs = []
        for node_id, node in existing_nodes.items():
            if node_id in self._node_embed_cache:
                emb = self._node_embed_cache[node_id]
            else:
                text = f"{node.name} {node.description}".strip()
                emb = self.embedding_model.encode(text)
                self._node_embed_cache[node_id] = emb
            ids.append(node_id)
            embs.append(emb)

        if not embs:
            return None

        matrix = np.vstack(embs)
        sims = cosine_similarity(candidate_emb, matrix)[0]
        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])

        if best_score >= self.dedup_threshold:
            return ids[best_idx]

        return None

    def _fuzzy_name_match(self, name: str, existing_nodes: dict[str, Node]) -> Optional[str]:
        """Last-resort fuzzy match for relation endpoints that missed exact match."""
        name_lower = name.lower()
        best_id = None
        best_score = 0.0

        for node_id, node in existing_nodes.items():
            for alias in node.aliases:
                # Simple token overlap ratio
                alias_tokens = set(alias.lower().split())
                name_tokens = set(name_lower.split())
                if not alias_tokens or not name_tokens:
                    continue
                overlap = len(alias_tokens & name_tokens) / max(len(alias_tokens), len(name_tokens))
                if overlap > best_score and overlap >= 0.6:
                    best_score = overlap
                    best_id = node_id

        return best_id

