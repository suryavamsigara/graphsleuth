import os
import uuid
from pathlib import Path
from typing import Callable

from graph import KnowledgeGraph, Node, Edge, Chunk, Document
from extractor import EntityExtractor


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


def chunk_by_paragraphs(text: str, max_chars: int = 500, overlap: int = 50) -> list[str]:
    """
    Splits text into paragraphs.
    """
    # Split on double newlines
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in raw_paragraphs:
        # If a single paragraph exceeds max_chars, split by sentences
        if len(para) > max_chars:
            sentences = split_into_sentences(para)
            for sent in sentences:
                if len(current_chunk) + len(sent) + 1 <= max_chars:
                    current_chunk += " " + sent if current_chunk else sent
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sent
            continue

        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += "\n\n" + para if current_chunk else para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para

    if current_chunk:
        chunks.append(current_chunk.strip())

    # Add overlap: each chunk starts with last overlap chars of previous
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i-1][-overlap:] if len(chunks[i-1]) > overlap else chunks[i-1]
            overlapped.append(prev_tail + "\n\n" + chunks[i])
        chunks = overlapped
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
