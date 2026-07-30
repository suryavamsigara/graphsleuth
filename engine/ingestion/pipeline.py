"""
Document ingestion pipeline for GraphSleuth

Orchestrates the full flow:
  Raw File -> Text Extraction -> Chunking -> Entity Extraction -> Graph Population
"""

import os
import uuid
from pathlib import Path
from typing import Callable

from engine.models.document import Chunk
from engine.graph.knowledge_graph import KnowledgeGraph
from engine.extraction.extractor import EntityExtractor
from engine.ingestion.chunking import chunk_by_paragraphs
from engine.ingestion.loaders import extract_text_from_file


# --------------------------------------------------------------
# Main ingestion orchestrator
# --------------------------------------------------------------

class IngestionPipeline:
    def __init__(
        self,
        kg: KnowledgeGraph,
        extractor: EntityExtractor,
        chunker: Callable[[str], list[str]] | None = None,
    ):
        self.kg = kg
        self.extractor = extractor
        self.chunker = chunker or chunk_by_paragraphs

    def ingest_file(self, file_path: str, file_name: str | None = None) -> dict:
        """
        Ingests a single file into the knowledge graph.
        """
        file_name = file_name or os.path.basename(file_path)
        try:
            # 1. Extract text
            raw_text = extract_text_from_file(file_path)
            print("RAW TEXT:\n\n", raw_text)
            if not raw_text.strip():
                return {
                    "success": False,
                    "error": "Empty file",
                    "document_id": None,
                    "chunks_processed": 0,
                    "nodes_created": 0,
                    "edges_created": 0
                }

            # 2. Chunk
            chunk_texts = self.chunker(raw_text)
            if not chunk_texts:
                return {
                    "success": False,
                    "error": "No chunks generated",
                    "document_id": None,
                    "chunks_processed": 0,
                    "nodes_created": 0,
                    "edges_created": 0,
                }

            # 3. Register document
            chunk_ids = [str(uuid.uuid4()) for _ in chunk_texts]
            doc_id = self.kg.register_document(file_path, file_name)
            if doc_id is None:
                return {
                    "success": True,
                    "error": "Duplicate document skipped",
                    "document_id": None,
                    "chunks_processed": 0,
                    "nodes_created": 0,
                    "edges_created": 0,
                }

            # 4. Process each chunk
            total_nodes = 0
            total_edges = 0

            for i, (chunk_text, chunk_id) in enumerate(zip(chunk_texts, chunk_ids)):
                # Store chunk
                chunk = Chunk(
                    id=chunk_id,
                    text=chunk_text,
                    document_id=doc_id,
                    index=i
                )
                self.kg.add_chunk(chunk)

                # Extract entities and relations
                new_nodes, new_edges = self.extractor.extract(
                    chunk_text=chunk_text,
                    chunk_id=chunk_id,
                    existing_nodes=self.kg.nodes,
                )

                print(20*"=")
                print("New Nodes: \n", new_nodes)
                print("New edges: \n", new_edges)
                print(20*"=")

                # Merge deduplicated nodes
                for node in new_nodes:
                    if node.id in self.kg.nodes:
                        self.kg.update_node_chunks(node.id, chunk_id)
                    else:
                        # New node
                        self.kg.add_node(node)
                        total_nodes += 1

                # Add edges
                for edge in new_edges:
                    try:
                        if self.kg.create_edge(edge):
                            total_edges += 1
                    except ValueError as e:
                        print(f"Skipping invalid edge: {e}")
                        continue

            return {
                "success": True,
                "document_id": doc_id,
                "chunks_processed": len(chunk_texts),
                "nodes_created": total_nodes,
                "edges_created": total_edges,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "document_id": None,
                "chunks_processed": 0,
                "nodes_created": 0,
                "edges_created": 0
            }

    def ingest_directory(self, dir_path: str, recursive: bool = True) -> list[dict]:
        """
        Ingest all supported files in a directory.
        Returns list of per-file results.
        """
        path = Path(dir_path)
        pattern = "**/*" if recursive else "*"
        supported = {".txt", ".md", ".py",".pdf"}

        files = [f for f in path.glob(pattern) if f.is_file() and f.suffix.lower() in supported]
        results = []
        for f in files:
            result = self.ingest_file(str(f), f.name)
            results.append(result)
            status = "OK" if result["success"] else "FAIL"
            print(f"  [{status}] {f.name}: "
                f"{result['chunks_processed']} chunks, "
                f"{result['nodes_created']} nodes, "
                f"{result['edges_created']} edges")
        return results

    def get_stats(self) -> dict:
        return self.kg.get_metrics()