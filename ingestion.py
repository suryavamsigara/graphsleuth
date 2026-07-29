"""
Document ingestion pipeline for GraphSleuth

Orchestrates the full flow:
  Raw File -> Text Extraction -> Chunking -> Entity Extraction -> Graph Population
"""

import os
import re
import uuid
from pathlib import Path
from typing import Callable

from engine.models.document import Chunk
from engine.graph.knowledge_graph import KnowledgeGraph
from engine.extraction.extractor import EntityExtractor


def extract_text_from_file(file_path: str) -> str:
    """
    Extracts raw text from a file.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    text_extensions = {".txt", ".md", ".py"}
    if suffix in text_extensions or suffix == "":
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Failed to read {file_path}: {e}")

    if suffix == ".pdf":
        try:
            import pypdf
            text = ""
            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() or ""
            return text
        except ImportError:
            raise ImportError("pypdf required for PDF support. Install: uv add pypdf")
        except Exception as e:
            raise ValueError(f"Failed to extract PDF {file_path}: {e}")

    raise ValueError(f"Unsupported file type: {suffix}. Supported: {text_extensions}")


def chunk_by_paragraphs(text: str, max_chars: int = 1200, overlap: int = 150) -> list[str]:
    """
    Splits text into chunks cleanly, respecting paragraph and sentence boundaries.
    Overlaps snap to word boundaries to prevent fragmented words, and strict length 
    limits are guaranteed.
    """
    
    # 1. Break text into an ordered stream of addressable semantic units
    def tokenize_text(raw_text: str):
        units = []
        for p in raw_text.split('\n\n'):
            p = p.strip()
            if not p:
                continue
            
            if len(p) <= max_chars:
                units.append((p, '\n\n'))
            else:
                # Fallback A: Paragraph is too big, split into sentences
                for s in re.split(r'(?<=[.!?])\s+', p):
                    s = s.strip()
                    if not s:
                        continue
                        
                    if len(s) <= max_chars:
                        units.append((s, ' '))
                    else:
                        # Fallback B: Sentence is STILL too big, split into words
                        for w in s.split():
                            if w.strip():
                                units.append((w.strip(), ' '))
        return units

    units = tokenize_text(text)
    chunks = []
    current_chunk = ""

    # 2. Reassemble units into chunks with safe overlapping
    for unit_text, separator in units:
        # Determine the connecting string
        prefix = separator if current_chunk else ""
        candidate = current_chunk + prefix + unit_text
        
        # If it fits, keep growing the chunk
        if len(candidate) <= max_chars:
            current_chunk = candidate
        else:
            # Chunk is full: Save it
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            # Seed the next chunk with the overlap from the saved chunk
            if overlap > 0 and current_chunk:
                tail = current_chunk[-overlap:]
                
                # Snap to the nearest word boundary (first space) to avoid slicing words
                space_idx = tail.find(' ')
                if space_idx != -1 and space_idx < len(tail) - 1:
                    current_chunk = tail[space_idx + 1:]
                else:
                    current_chunk = tail  # Fallback if no spaces exist
            else:
                current_chunk = ""
                
            # Add the current unit to the newly seeded chunk
            prefix = separator if current_chunk else ""
            if len(current_chunk) + len(prefix) + len(unit_text) <= max_chars:
                current_chunk = current_chunk + prefix + unit_text
            else:
                # Edge case: Overlap + new unit exceeds max_chars.
                # Drop the overlap to strictly enforce character limits.
                current_chunk = unit_text

    # 3. Append the final remaining chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def split_into_sentences(text: str) -> list[str]:
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


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
            doc_id = self.kg.register_document(file_path, file_name, chunk_ids)
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