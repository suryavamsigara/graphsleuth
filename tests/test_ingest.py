import os
import tempfile

from engine.ingestion.pipeline import IngestionPipeline
from engine.ingestion.chunking import chunk_by_paragraphs
from engine.graph.knowledge_graph import KnowledgeGraph

class DummyStore:
    def __init__(self): 
        self.nodes, self.chunks, self.documents, self.edges = {}, {}, {}, []

    def load_nodes(self, pid): return dict(self.nodes)
    def load_chunks(self, pid): return dict(self.chunks)
    def load_documents(self, pid): return dict(self.documents)
    def load_edges(self, pid): return list(self.edges)
    def save_node(self, node): self.nodes[node.id] = node
    def save_document(self, doc): self.documents[doc.id] = doc
    def save_edge(self, edge): self.edges.append(edge); return True
    def save_chunk(self, chunk): self.chunks[chunk.id] = chunk


class DummyVectorStore:
    def upsert_node_embedding(self, nid, emb): pass


class DummyEncoder:
    def encode_single(self, text): return [0.1, 0.2]


class DummyExtractor:
    def extract(self, chunk_text, chunk_id, existing_nodes):
        return [], []


# --- Tests ---

def test_chunking():
    text = (
        "GraphRAG combines vector database indexing with structured knowledge graph traversal. "
        "By turning paragraphs into discrete entities and edges, complex multi-hop queries become trivial.\n\n"
        "Chunking is the critical first stage of document processing. A bad chunker destroys context "
        "or splits words across arbitrary character boundaries. Proper paragraph snapping is mandatory.\n\n"
        + ("This is a long synthetic paragraph designed to force sentence and word fallback splitting. " * 30)
    )
    chunks = chunk_by_paragraphs(text, max_chars=150, overlap=50)
    assert len(chunks) > 2


def test_ingest_file():
    kg = KnowledgeGraph("test_proj", DummyStore(), DummyVectorStore(), DummyEncoder())
    pipeline = IngestionPipeline(kg=kg, extractor=DummyExtractor())

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f:
        text = (
            "GraphRAG combines vector database indexing with structured knowledge graph traversal. "
            "By turning paragraphs into discrete entities and edges, complex multi-hop queries become trivial.\n\n"
            "Chunking is the critical first stage of document processing. A bad chunker destroys context "
            "or splits words across arbitrary character boundaries. Proper paragraph snapping is mandatory.\n\n"
            + ("This is a long synthetic paragraph designed to force sentence and word fallback splitting. " * 30)
        )
        f.write(text)
        tmp_path = f.name

    try:
        res = pipeline.ingest_file(tmp_path)
        assert res["success"] is True, f"Ingestion failed: {res.get('error')}"
        assert res["chunks_processed"] > 2
    finally:
        os.remove(tmp_path)


def test_ingest_empty_file():
    kg = KnowledgeGraph("test_proj", DummyStore(), DummyVectorStore(), DummyEncoder())
    pipeline = IngestionPipeline(kg=kg, extractor=DummyExtractor())

    with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".txt") as f:
        f.write("   ")
        tmp_path = f.name

    try:
        res = pipeline.ingest_file(tmp_path)
        assert res["success"] is False, "Empty file should fail ingestion"
    finally:
        os.remove(tmp_path)


if __name__ == "__main__":
    for test in [test_chunking, test_ingest_file, test_ingest_empty_file]:
        test()
        print(f"[PASS] {test.__name__}")