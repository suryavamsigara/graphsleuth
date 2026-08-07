import os
import tempfile

from engine.graph.knowledge_graph import KnowledgeGraph
from engine.models.node import Node
from engine.models.edge import Edge


class DummyGraphStore:
    def __init__(self):
        self.nodes, self.chunks, self.documents, self.edges = {}, {}, {}, []

    def load_nodes(self, pid): return dict(self.nodes)
    def load_chunks(self, pid): return dict(self.chunks)
    def load_documents(self, pid): return dict(self.documents)
    def load_edges(self, pid): return list(self.edges)
    def save_node(self, node): self.nodes[node.id] = node
    def save_document(self, doc): self.documents[doc.id] = doc
    def save_edge(self, edge): self.edges.append(edge); return True
    def delete_node(self, nid): self.nodes.pop(nid, None)


class DummyVectorStore:
    def upsert_node_embedding(self, nid, emb): pass


class DummyEncoder:
    def encode_single(self, text): return [0.1, 0.2, 0.3]


def make_node(id: str, name: str, source_chunk_ids: list[str] = None) -> Node:
    return Node(
        id=id,
        aliases=[name],
        node_type="ENTITY",
        description="",
        source_chunk_ids=source_chunk_ids or [],
    )


class TestKnowledgeGraph:
    def setUp(self):
        self.store = DummyGraphStore()
        self.kg = KnowledgeGraph(
            project_id="test_proj",
            store=self.store,
            vector_store=DummyVectorStore(),
            encoder=DummyEncoder(),
        )

    def test_register_document_deduplication(self):
        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write("Sample document body for checksum validation")
            tmp_path = f.name

        try:
            doc_id_1 = self.kg.register_document(tmp_path, "file.txt")
            doc_id_2 = self.kg.register_document(tmp_path, "file.txt")

            assert doc_id_1 is not None, "First registration should return a document ID"
            assert doc_id_2 is None, "Duplicate document should return None"
        finally:
            os.remove(tmp_path)

    def test_add_node_and_update_chunks(self):
        node = make_node(id="n1", name="Alpha", source_chunk_ids=["chunk_a"])
        self.kg.add_node(node)

        assert self.kg.get_node("n1").name == "Alpha", "Node name mismatch"

        self.kg.update_node_chunks("n1", "chunk_a")
        self.kg.update_node_chunks("n1", "chunk_b")
        assert self.kg.get_node("n1").source_chunk_ids == ["chunk_a", "chunk_b"], "Chunk IDs not deduplicated/merged correctly"

    def test_edge_validations_and_self_loops(self):
        self.kg.add_node(make_node(id="n1", name="Node 1"))
        self.kg.add_node(make_node(id="n2", name="Node 2"))

        # Check missing target node raises ValueError
        raised_missing = False
        try:
            self.kg.create_edge(Edge(id="e1", source_id="n1", target_id="missing_id", relation="LINK", source_chunk_id="123"))
        except ValueError:
            raised_missing = True
        assert raised_missing, "Expected ValueError for non-existent target node"

        # Check self loop raises ValueError
        raised_loop = False
        try:
            self.kg.create_edge(Edge(id="e2", source_id="n1", target_id="n1", relation="LOOP", source_chunk_id="123"))
        except ValueError:
            raised_loop = True
        assert raised_loop, "Expected ValueError for self loop"

        # Check valid edge creation
        valid = self.kg.create_edge(Edge(id="e3", source_id="n1", target_id="n2", relation="LINK", source_chunk_id="123"))
        assert valid is True, "Valid edge should return True"
        assert len(self.kg.get_outgoing_edges("n1")) == 1, "Outgoing edge count should be 1"

    def test_delete_node_cascades_edges(self):
        self.kg.add_node(make_node(id="n1", name="Node 1"))
        self.kg.add_node(make_node(id="n2", name="Node 2"))
        self.kg.create_edge(Edge(id="e1", source_id="n1", target_id="n2", relation="LINK", source_chunk_id="123"))

        self.kg.delete_node("n1")

        assert self.kg.get_node("n1") is None, "Node n1 should be deleted"
        assert len(self.kg.get_outgoing_edges("n1")) == 0, "Outgoing edges for n1 should be 0"
        assert len(self.kg.get_incoming_edges("n2")) == 0, "Incoming edges for n2 should be cleared"

    def test_get_central_nodes(self):
        self.kg.add_node(make_node(id="hub", name="Hub Node"))
        self.kg.add_node(make_node(id="n1", name="Node 1"))
        self.kg.add_node(make_node(id="n2", name="Node 2"))

        self.kg.create_edge(Edge(id="e1", source_id="hub", target_id="n1", relation="LINK", source_chunk_id="123"))
        self.kg.create_edge(Edge(id="e2", source_id="hub", target_id="n2", relation="LINK", source_chunk_id="123"))

        top_nodes = self.kg.get_central_nodes(top_k=1)
        assert top_nodes[0] == ("hub", 2), f"Expected ('hub', 2), got {top_nodes[0]}"


def run_tests():
    test_suite = TestKnowledgeGraph()
    test_methods = [
        m for m in dir(test_suite) if m.startswith("test_") and callable(getattr(test_suite, m))
    ]

    passed = 0
    failed = 0

    print(f"Running {len(test_methods)} tests...\n" + "-" * 50)

    for method_name in test_methods:
        test_suite.setUp()
        test_fn = getattr(test_suite, method_name)
        try:
            test_fn()
            print(f"  [PASS] {method_name}")
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {method_name}: {e}")
            failed += 1

    print("-" * 50)
    print(f"Results: {passed} Passed, {failed} Failed.")
    if failed > 0:
        exit(1)


if __name__ == "__main__":
    run_tests()