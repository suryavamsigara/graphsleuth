"""
Entity & Relation extraction pipeline for GraphSleuth

Takes raw text chunks, calls an LLM, and returns structured
Node and Edge objects ready for ingestion into KnowledgeGraph.
"""

import json
import re
import httpx
import time
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from engine.embeddings.encoder import EmbeddingEncoder
from engine.client import get_ollama, get_openai
from engine.models.node import Node
from engine.models.edge import Edge
from engine.extraction.prompts import EXTRACTION_PROMPT
from engine.extraction.schemas import ExtractionResult


class EntityExtractor:
    """
    Extracts Node and Edge objects from text chunks.
    """
    def __init__(
        self,
        model_name: str = "qwen3.5:4b",
        use_local: bool = True,
        encoder: EmbeddingEncoder | None = None,
        dedup_threshold: float = 0.85,
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: int = 120
    ):
        self.use_local = use_local
        self.client = get_ollama() if self.use_local else get_openai()
        self.model_name = model_name
        self.encoder = encoder
        self.dedup_threshold = dedup_threshold
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        self._node_embed_cache: dict[str, np.ndarray] = {}

    def extract(
        self,
        chunk_text: str,
        chunk_id: str,
        existing_nodes: dict[str, Node] | None = None,
    ) -> tuple[list[Node], list[Edge]]:
        """Extracts nodes and edges from a single chunk."""
        print("Extracting...")
        raw_json = self._call_llm_with_retry(chunk_text)
        parsed = ExtractionResult.model_validate(raw_json)
        print("Extracted!")

        nodes_dict: dict[str, Node] = {}
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
                nodes_dict[matched_node_id] = existing_nodes[matched_node_id]

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
                nodes_dict[node.id] = node
                name_to_node_id[canonical_name] = node.id
                for alias in ent.aliases:
                    name_to_node_id[alias.strip()] = node.id

        edges: list[Edge] = []
        for rel in parsed.relations:
            src_name = rel.source.strip()
            tgt_name = rel.target.strip()


            src_id = name_to_node_id.get(src_name)
            tgt_id = name_to_node_id.get(tgt_name)

            if src_id is None:
                src_id = self._fuzzy_name_match(src_name, nodes_dict)
                if src_id is None and existing_nodes:
                    src_id = self._fuzzy_name_match(src_name, existing_nodes)
            
            if tgt_id is None:
                tgt_id = self._fuzzy_name_match(tgt_name, nodes_dict)
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
        return list(nodes_dict.values()), edges


    def _call_llm_with_retry(self, chunk_text: str):
        prompt = EXTRACTION_PROMPT.replace("{chunk_text}", chunk_text.strip())
        print(chunk_text.strip())

        messages = [
            {"role": "system", "content": "You are a precise data extraction system. Always respond with raw JSON matching the expected format. CRUCIAL: Every entity must include the 'aliases' list field, even if it is empty []."},
            {"role": "user", "content": prompt}
        ]

        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                current_timeout = 600.0 if self.use_local else self.timeout

                kwargs = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": False,
                    "temperature": self.temperature,
                    "timeout": httpx.Timeout(current_timeout),
                }

                if not self.use_local:
                    kwargs["response_format"] = {"type": "json_object"}
                else:
                    # kwargs["max_completion_tokens"] = 2048
                    kwargs["extra_body"] = {
                        "response_format": {
                            "type": "json_object",
                            "schema": ExtractionResult.model_json_schema()
                        },
                        "options": {
                            # "num_ctx": 8192,
                            "temperature": 0.0,
                            "num_thread": 4,
                            "numa": False,
                            "low_vram": True,
                            "num_ctx": 4096,
                            "use_mmap": True,
                            "f16_kv": True
                        }
                    }

                response = self.client.chat.completions.create(**kwargs)
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
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON cleanly: {e}")

    def _find_duplicate(
        self,
        name: str,
        description: str,
        existing_nodes: dict[str, Node] | None,
    ) -> str | None:
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
        candidate_emb = np.array(self.encoder.encode_single(candidate_text)).reshape(1, -1)

        ids: list[str] = []
        embs: list[np.ndarray] = []
        for node_id, node in existing_nodes.items():
            if node_id in self._node_embed_cache:
                emb = self._node_embed_cache[node_id]
            else:
                text = f"{node.name} {node.description}".strip()
                emb = np.array(self.encoder.encode_single(text))
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

    def _fuzzy_name_match(self, name: str, existing_nodes: dict[str, Node]) -> str | None:
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

