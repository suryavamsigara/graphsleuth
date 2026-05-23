import json
from pathlib import Path
from model2vec import StaticModel

from client import get_client
from chunker import Chunk, Chunker
from graph import Node, Edge, KnowledgeGraph

root = Path(__file__).parent

class Ingestion:
    def __init__(self):
        self.embedding_model = StaticModel.from_pretrained("MinishLab/potion-retrieval-32M", dimensionality=128)
        self.chunker = Chunker(chunk_size=300)
        self.graph = KnowledgeGraph(self.embedding_model)

        self.client = get_client()
        self.file_content = ""
    
    def run(self, file_path: str):
        file = root / file_path

        with open(file, "r", encoding="utf-8") as f:
            self.file_content = f.read()
        
        print("\nChunking file content...")
        chunks_list = self.chunker.chunk_content(self.file_content)
        print("\nExtracting entities..")
        extracted = self.extract(chunks_list, file_path)
        print("\nCreating graph")
        self.add_entites_and_triples(extracted, file_path)


    # will Replace source_doc with doc_id
    def extract(self, chunks_list: list[list[str]], source_doc: str) -> dict[str, list]:
        """
        Takes a chunk, calls LLM, returns entities and triples as dicts
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

        for i, chunk in enumerate(chunks_list[:2]):
            chunk_text = ' '.join(chunk).strip(',')

            chunk_id = self.chunker.create_chunk(chunk_text, source_doc, i)

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

            # response = self.client.chat.completions.create(
            #     model="deepseek-v4-flash",
            #     messages=messages,
            #     temperature=0.2,
            #     response_format={"type": "json_object"}
            # )

            # raw_content = response.choices[0].message.content
            raw_content = ""

            if raw_content.startswith("```json"):
                raw_content = raw_content[7:]
            elif raw_content.startswith("```"):
                raw_content = raw_content[3:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
            raw_content = raw_content.strip()

            try:
                chunk_result = json.loads(raw_content)
            except json.JSONDecodeError as e:
                print(f"JSON parse error in chunk {i}: {e}")
                print(f"Raw content: {raw_content[:200]}..")
                continue

            chunk_result_test = {
                "entities": [
                    {"name": "Attention mechanism", "type": "concept"},
                    {"name": "RNN", "type": "concept"}
                ],

                "triples": [
                    {"subject": "Attention mechanism", "predicate": "allows", "object": "focus on input positions"},
                    {"subject": "Attention mechanism", "predicate": "differs from", "object": "RNN"}
                ]
            }

            """
            later validation check: check entity has name, type
            every triple has subj, pred, obj.
            """

            for entity in chunk_result_test.get("entities", []):
                entity["chunk_id"] = chunk_id
            
            for triple in chunk_result_test.get("triples", []):
                triple["chunk_id"] = chunk_id
            
            aggregated["entities"].extend(chunk_result_test.get("entities", []))
            aggregated["triples"].extend(chunk_result_test.get("triples", []))
        
        return aggregated
    
    def add_entites_and_triples(self, entities_and_triples: dict[str, list], source_doc: str):
        entities = entities_and_triples["entities"]
        triples = entities_and_triples["triples"]

        node_map = {}

        for entity in entities:
            name = entity["name"].strip()

            node = Node(
                node_type=entity["type"],
                aliases=[name],
                source_chunk_ids=[entity["chunk_id"]]
            )
            
            node_id = self.graph.add_node(node) # Same id as node.id if not merged, else existing id

            node_map[name] = node_id
        
        for triple in triples:
            subj = triple["subject"].strip()
            pred = triple["predicate"].strip()
            obj = triple["object"].strip()

            if subj in node_map and obj in node_map:
                edge = Edge(
                    source_id=node_map[subj],
                    target_id=node_map[obj],
                    relation=pred,
                    source_chunk_id=triple["chunk_id"]
                )
                self.graph.create_edge(edge)
            
            """
            (later)
            For else cond. (if obj ain't in node_map), auto-create it as a Node
            of type 'concept' with low confidence.
            """

if __name__ == "__main__":
    ingestor = Ingestion()

    ingestor.run("file.txt")
    print("GRAPH")
    ingestor.graph.print_graph()
    print("\nChunks")
    print(ingestor.chunker.get_chunks())

