from pathlib import Path
from collections import defaultdict
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

SYSTEM_PROMPT = ""

def extract(chunks: list[str], source_doc: str, client):
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


    result: dict[str, list[dict[str, str]]] = defaultdict(list)

    for chunk in chunks:
        response = client.chat.completions() # Returns JSON
        
        result = response.content


        # raw chunk goes to a chunk table, tagged with which doc or page it came from.

    return result

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
            source_doc=source_doc,
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
                source_doc=source_doc
            )
            graph.create_edge(edge)

add_entities_and_triples(res, "file.txt", graph)
