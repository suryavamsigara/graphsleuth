
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