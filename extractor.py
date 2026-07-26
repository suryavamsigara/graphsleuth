import json
import re
import httpx
import time
import numpy as np
from typing import Optional, Literal
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from client import get_ollama, get_openai

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
    relation: Literal[
        "compared_to", 
        "implements", 
        "conceptually_similar_to", 
        "matches_performance_of",
        "introduced_in",
        "uses",
        "alternative_to"
    ] = Field(
        description="The exact structural predicate linking source and target entities."
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
- Include 1-2 sentence descriptions grounded in the text.
- Add aliases only if the text explicitly uses alternative names.
- Relations must use simple, exact predicates matching the schema constraints: compared_to, hybridized_with, implements, conceptually_similar_to, uses, alternative_to.
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
        temperature: float = 0.0,
        max_retries: int = 3,
        timeout: int = 120
    ):
        self.client = get_ollama()
        self.model_name = model_name
        self.embedding_model = embedding_model
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

    def extract(self, chunk_text: str, chunk_id: str):
        """Extracts nodes and edges from a single chunk."""
        raw_json = self._call_llm_with_retry(chunk_text)
        return raw_json


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
                            "top_k": 40,
                            "top_p": 0.9,
                            "repeat_penalty": 1.1,
                            "presence_penalty": 0.6
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

if __name__=="__main__":
    e = EntityExtractor()
    text = """
    Ilya Sutskever, a student of Hinton, has stated that "the Transformer is not the final architecture." In a 2024 interview, he suggested future systems might combine symbolic reasoning with pattern matching. Sutskever left OpenAI in 2025 to found Safe Superintelligence Inc., focusing on alignment before capability.
    """
    print(e.extract(text, "12345"))