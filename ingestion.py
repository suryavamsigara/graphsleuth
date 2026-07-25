import re
import json
import numpy as np
from pathlib import Path
from gliner import GLiNER
from model2vec import StaticModel
from sklearn.metrics.pairwise import cosine_similarity

from client import get_client
from chunker import Chunker
from graph import Node, Edge, KnowledgeGraph

root = Path(__file__).parent

LABELS = {
    "Person",
    "Organization",
    "Location",
    "Technology or Software", 
    "Creative Work", 
    "Event", 
    "Concept or Theory"
}

class Ingestion:
    def __init__(self):
        print("Loading models..")
        self.embedding_model = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M", dimensionality=128
        )
        self.querying_model = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M"
        ) # 512
        self.ner_model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")

        self.chunker = Chunker(chunk_size=200)
        self.graph = KnowledgeGraph(self.embedding_model, self.querying_model)
        self.client = get_client()
    
    def run(self, file_path: str):
        file = root / file_path
        doc_hash = self.graph.calculate_checksum(str(file))
        if doc_hash in self.graph.doc_checksums:
            print(f"'{file.name}' already ingested.")
            return

        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
        
        print("\nChunking file content...")
        chunks = self.chunker.chunk_content(
            content=file_content,
            source_doc=file_path
        )

        processed_chunk_ids = []

        # Pass 1: Global entity discovery
        print("\nPass 1: Discovering entities globally...")
        raw_global_entities = {}

        for chunk in chunks:
            self.graph.add_chunk(chunk)
            processed_chunk_ids.append(chunk.id)
            
            chunk_entities = self.extract_entities(chunk.text)
            for name, data in chunk_entities.items():
                if name not in raw_global_entities:
                    raw_global_entities[name] = data
                raw_global_entities[name]["chunk_ids"].add(chunk.id)
        
        print("\n", raw_global_entities)

        # Entity resolution
        resolved_entities = self.resolve_entities(raw_global_entities)
        print(f"\nRESOLVED: {resolved_entities}\n")

        # Pass 2: Relation extraction
        all_relations = []
        canonical_names = list(resolved_entities.keys())

        for chunk in chunks:
            relations = self.extract_relations(chunk.text, canonical_names)
            for rel in relations:
                rel["chunk_id"] = chunk.id
            all_relations.extend(relations)

        # Graph insertion
        self.insert_into_graph(resolved_entities, all_relations)
        self.graph.register_document(file_path=str(file), file_name=file.name, chunk_ids=processed_chunk_ids)

        print("Ingestion execution completed successfully.")

    def extract_entities(self, chunk_text: str) -> dict:
        raw_entities = self.ner_model.predict_entities(chunk_text, LABELS, threshold=0.4)
        print(f"\nRAW: {raw_entities}\n")
        unique = {}
        for ent in raw_entities:
            name = ent["text"].strip()
            if len(name) < 2 or name.lower() in {"it", "they", "we", "he", "she", "paper", "recent publications", "validating the theory"}:
                continue
            unique[name] = {"type": ent["label"], "chunk_ids": set()}
        return unique
    
    def resolve_entities(self, raw_entities: dict) -> dict:
        if not raw_entities: return {}
        
        names = sorted(list(raw_entities.keys()), key=len, reverse=True)
        embeddings = np.array([self.embedding_model.encode(n).flatten() for n in names])
        
        canonical_map = {}
        merged_indices = set()

        print("RAW: ", raw_entities)
        print()
        print("NAMES: ", names)

        for i, name in enumerate(names):
            if i in merged_indices: continue
            
            type_i = raw_entities[name]["type"]
            canonical_map[name] = {
                "type": type_i,
                "aliases": {name},
                "chunk_ids": set(raw_entities[name]["chunk_ids"])
            }
            
            for j in range(i + 1, len(names)):
                if j in merged_indices: continue
                
                target = names[j]
                type_j = raw_entities[target]["type"]
                is_match = False
                
                # Rule 1: Whole-word Substring Match + Same Category
                if type_i == type_j and re.search(rf'\b{re.escape(target.lower())}\b', name.lower()):
                    is_match = True
                
                # Rule 2: Acronym Match + Same Category
                elif type_i == type_j:
                    acronym = "".join([w[0] for w in name.split() if w[0].isalpha()]).upper()
                    if acronym == target.upper():
                        is_match = True
                    
                # Rule 3: Vector Similarity + Same Category
                if not is_match:
                    sim = cosine_similarity(embeddings[i].reshape(1, -1), embeddings[j].reshape(1, -1))[0][0]
                    if sim > 0.88 and type_i == type_j:
                        is_match = True

                if is_match:
                    canonical_map[name]["aliases"].add(target)
                    canonical_map[name]["chunk_ids"].update(raw_entities[target]["chunk_ids"])
                    merged_indices.add(j)

        return canonical_map
    
    def extract_relations(self, text: str, canonical_names: list[str]) -> list[dict]:
        if not canonical_names: return []
            
        entity_list_str = "\n".join([f"- {name}" for name in canonical_names])
        messages = [
            {
                "role": "system",
                "content": f"""You extract factual relationships from text to build a Knowledge Graph. 
                                
                CRITICAL RULE: You are ONLY allowed to use the exact entity names from the list below as the 'subject' or 'object'. 
                Do NOT invent or extract any entities not on this list:
                {entity_list_str}

                Predicate Rules:
                - Use short, descriptive verb phrases (e.g., "introduced", "differs from").
                Return valid JSON only:
                {{
                    "triples": [
                        {{"subject": "Entity1", "predicate": "verb", "object": "Entity2"}}
                    ]
                }}"""
            },
            {"role": "user", "content": f"Text: {text}"}
        ]

        try:
            response = self.client.chat.completions.create(
                model="deepseek-v4-flash",
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```json"):
                raw = raw[7:-3]
            elif raw.startswith("```"):
                raw = raw[3:-3]
                
            data = json.loads(raw)
            
            valid_triples = []
            for t in data.get("triples", []):
                if t.get("subject") in canonical_names and t.get("object") in canonical_names:
                    valid_triples.append(t)
            return valid_triples

        except Exception:
            return []
        
    def insert_into_graph(self, resolved_entities: dict, relations: list[dict]):
        node_map = {} 

        for canonical_name, data in resolved_entities.items():
            node = Node(
                node_type=data["type"],
                aliases=list(data["aliases"]),
                description="", 
                source_chunk_ids=list(data["chunk_ids"])
            )
            node_id = self.graph.add_node(node)
            node_map[canonical_name] = node_id

        for triple in relations:
            edge = Edge(
                source_id=node_map[triple["subject"]],
                target_id=node_map[triple["object"]],
                relation=triple["predicate"],
                source_chunk_id=triple["chunk_id"]
            )
            self.graph.create_edge(edge)

if __name__ == "__main__":
    pipeline = Ingestion()

    pipeline.run("file.txt")
    print("GRAPH\n")
    pipeline.graph.print_graph()
    print("\nEDGES COUNT: ")
    print(pipeline.graph._get_total_edges_count())
    print("\nResponse: ")
    print(pipeline.graph.query("What is optimal sequence modelling?", max_depth=3))
    print("\nCHUNKS\n")
    print(pipeline.graph.get_chunks())

