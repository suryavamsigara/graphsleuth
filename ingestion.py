import json
from pathlib import Path
from model2vec import StaticModel

from client import get_client
from chunker import Chunker
from graph import Node, Edge, KnowledgeGraph

root = Path(__file__).parent

class Ingestion:
    def __init__(self):
        self.embedding_model = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M", dimensionality=128
        )
        self.querying_model = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M"
        ) # 512

        self.chunker = Chunker(chunk_size=200)
        self.graph = KnowledgeGraph(self.embedding_model, self.querying_model)

        self.client = get_client()
        self.file_content = ""
    
    def run(self, file_path: str):
        file = root / file_path

        doc_hash = self.graph.calculate_checksum(str(file))
        if doc_hash in self.graph.doc_checksums:
            print(f"Skipping pipeline: '{file.name}' already ingested.")
            return

        with open(file, "r", encoding="utf-8") as f:
            self.file_content = f.read()
        
        print("\nChunking file content...")
        chunks = self.chunker.chunk_content(
            content=self.file_content,
            source_doc=file_path
        )

        processed_chunk_ids = []

        for chunk in chunks[:3]:
            self.graph.add_chunk(chunk)
            processed_chunk_ids.append(chunk.id)

            print("Extracting from chunks..")
            e_and_t = self.extract_chunk(chunk.text, chunk.id)

            print("Creating graph..")
            self.add_entites_and_triples(e_and_t)
        
        self.graph.register_document(
            file_path=str(file),
            file_name=file.name,
            chunk_ids=processed_chunk_ids
        )
        print("Ingestion execution completed successfully.")


    # will Replace source_doc with doc_id
    def extract_chunk(self, chunk_text: str, chunk_id: str) -> dict[str, list]:
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

        messages = [
            {
                "role": "system",
                "content": """You extract entities and triples from text to build a Knowledge Graph. Do not over extract. Do not extract generic abstract nouns.
                CRITICAL: For every entity, write a detailed description containing exactly 20 to 25 words. 
                OPTIMIZATION RULE: Frame the description to optimize future vector search queries. Focus heavily on technical characteristics, actions, associations, and domain-specific keywords present in the text. Avoid conversational padding.
                Return valid JSON only. No markdown, no explanation.
                Example output format: 
                {
                    "entities": [
                        {
                            "name": "Attention mechanism",
                            "type": "concept",
                            "description": "An architectural component in neural networks that enables models to dynamically focus on specific segments of input sequences, improving long-range dependency tracking."
                        },
                        {
                            "name": "RNN",
                            "type": "concept",
                            "description": "A class of artificial neural networks where connections between nodes form a directed graph along a temporal sequence, allowing processing of variable length inputs."
                        }
                    ],

                    "triples": [
                        {"subject": "Attention mechanism", "predicate": "allows", "object": "focus on input positions"},
                        {"subject": "Attention mechanism", "predicate": "differs from", "object": "RNN"}
                    ]
                }"""
            },
            {"role": "user", "content": f"Text: {chunk_text}"}
        ]
        print("LLM CALL")
        response = self.client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=messages,
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        print("LLM CALL ENDED")

        raw_content = response.choices[0].message.content
        # raw_content = ""

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
            print(f"JSON parse error in chunk: {e}")
            return {"entities": [], "triples": []}

        # chunk_result_test = {
        #     "entities": [
        #         {"name": "Attention mechanism", "type": "concept", "description": "An architectural component in neural networks that enables models to dynamically focus on specific segments of input sequences, improving long-range dependency tracking."},
        #         {"name": "RNN", "type": "concept", "description": "A class of artificial neural networks where connections between nodes form a directed graph along a temporal sequence, allowing processing of variable length inputs."}
        #     ],

        #     "triples": [
        #         {"subject": "Attention mechanism", "predicate": "allows", "object": "focus on input positions"},
        #         {"subject": "Attention mechanism", "predicate": "differs from", "object": "RNN"}
        #     ]
        # }

        """
        later validation check: check entity has name, type
        every triple has subj, pred, obj.
        """

        for entity in chunk_result.get("entities", []):
            entity["chunk_id"] = chunk_id
        
        for triple in chunk_result.get("triples", []):
            triple["chunk_id"] = chunk_id

        return {
            "entities": chunk_result.get("entities", []),
            "triples": chunk_result.get("triples", [])
        }

    
    def add_entites_and_triples(self, entities_and_triples: dict[str, list]):
        entities = entities_and_triples["entities"]
        triples = entities_and_triples["triples"]

        node_map = {}

        for entity in entities:
            name = entity["name"].strip()

            node = Node(
                node_type=entity["type"],
                aliases=[name],
                description=entity["description"],
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
    pipeline = Ingestion()

    pipeline.run("file.txt")
    print("GRAPH")
    pipeline.graph.print_graph()
    print("\nChunks")
    print(pipeline.graph.get_chunks())

