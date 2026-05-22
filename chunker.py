import uuid
import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field

from client import get_client
from graph import Node, Edge, KnowledgeGraph

root = Path(__file__).parent
file = root / 'file.txt'

with open(file, 'r', encoding='utf-8') as f:
    words = f.read().split(' ')


print(len(words))

def chunk_content(words: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []

    for i in range(0, len(words), 60):
        chunks.append(words[i:i+60])
    
    return chunks

@dataclass(frozen=True)
class Chunk:
    text: str
    source_doc: str
    index: int
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

class Chunks:
    def __init__(self):
        self.chunks_list = []
    
    def add_chunk(self, chunk: Chunk):
        self.chunks_list.append(chunk)

    def print_chunks(self):
        return self.chunks_list

def extract(chunks: list[str], source_doc: str, client, chunk_obj: Chunks):
    """
    Sends each chunk to an LLM. LLM returns entities and triples.

    entities:
        - "Attention mechanism"   -> concept
        - "RNN"                   -> concept
        - "Vaswani et al."        -> person
        - "Transformer"           -> concept
    
    triples:
        - (Attention mechanism, allows, focus on input positions)
        - (Attention mechanism, differs from, RNN)
        - (Vaswani et al., introduced, scaled dot-product attention)
        - (Transformer, uses, Attention mechanism)
    """

    aggregated = {
        "entities": [],
        "triples": []
    }

    for i, chunk in enumerate(chunks[:2]):
        chunk_text = ' '.join(chunk).strip(',')

        # raw chunk goes to a chunk table, tagged with which doc or page it came from.
        updated_chunk = Chunk(
            text=chunk_text,
            source_doc=source_doc,
            index=i
        )
        chunk_obj.add_chunk(updated_chunk)

        messages = [
            {"role": "system", "content": """You extract entities and triples from text.Do not over extract. Do not extract generic abstract nouns.
             Return valid JSON only. No markdown, no explanation. example: 
            "entities": [
                {"name": "Attention mechanism", "type": "concept"},
                {"name": "RNN", "type": "concept"}
            ],

            "triples": [
                {"subject": "Attention mechanism", "predicate": "allows", "object": "focus on input positions"},
                {"subject": "Attention mechanism", "predicate": "differs from", "object": "RNN"}
            ]
             """},
            {"role": "user", "content": f"Text: {chunk_text}"}
        ]

        response = client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        
        chunk_result = json.loads(response.choices[0].message.content)

        for entity in chunk_result.get("entities", []):
            entity["chunk_id"] = updated_chunk.id
        for triple in chunk_result.get("triples", []):
            triple["chunk_id"] = updated_chunk.id

        aggregated["entities"].extend(chunk_result.get("entities", []))
        aggregated["triples"].extend(chunk_result.get("triples", []))

    return aggregated

client = get_client()

chunks = chunk_content(words)
chunk_obj = Chunks()

extracted_content = extract(chunks, "file.txt", client, chunk_obj)
print(extracted_content)
print(chunk_obj.print_chunks())


res = {
    "entities": [
        {"name": "Attention mechanism", "type": "concept"},
        {"name": "RNN", "type": "concept"}
    ],

    "triples": [
        {"subject": "Attention mechanism", "predicate": "allows", "object": "focus on input positions"},
        {"subject": "Attention mechanism", "predicate": "differs from", "object": "RNN"}
    ]
}

graph = KnowledgeGraph()

def add_entities_and_triples(result, source_doc: str, graph: KnowledgeGraph):
    entities = result["entities"]
    triples = result["triples"]

    node_map = {}

    for entity in entities:
        name = entity["name"]
        # Embed entity, cosine sum with embedding matrix, if any > 0.9, merge, else new node
        node = Node(
            node_type=entity["type"],
            aliases=[entity["name"]],
            source_chunk_id=entity["chunk_id"]
        )

        graph.add_node(node)

        node_map[name] = node.id
    
    for triple in triples:
        subj = triple["subject"]
        pred = triple["predicate"]
        obj = triple["object"]

        if subj in node_map and obj in node_map:
            edge = Edge(
                source_id=node_map[subj],
                target_id=node_map[obj],
                relation=pred,
                source_chunk_id=triple["chunk_id"]
            )
            graph.create_edge(edge)
    
    return graph.nodes

nodes = add_entities_and_triples(extracted_content, "file.txt", graph)
print(nodes)
graph.print_graph()