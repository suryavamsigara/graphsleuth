"""
Knowledge Graph Core + Persistence + Evidence Tracking
"""


import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

from engine.ports.graph_store import GraphStore
from engine.ports.vector_store import VectorStore
from engine.embeddings.encoder import EmbeddingEncoder
from engine.models.node import Node
from engine.models.edge import Edge
from engine.models.document import Chunk, Document, EvidencePath
from engine.graph.traversal import TraversalEngine

# ---------------------------------------------------------------------------
# Knowledge Graph (in memory cache + SQLite persistence)
# ---------------------------------------------------------------------------

class KnowledgeGraph:
    """
    The main graph interface. All data lives in SQLite.
    """
    def __init__(
        self,
        project_id: str,
        store: GraphStore,
        vector_store: VectorStore,
        encoder: EmbeddingEncoder,
        min_entry_score: float = 0.35,
        guided_traversal_min_score: float = 0.20,
        beam_width: int = 3,
    ):
        self.project_id = project_id
        self.store = store
        self.vector_store = vector_store
        self.encoder = encoder
        self.min_entry_score = min_entry_score
        self.guided_traversal_min_score = guided_traversal_min_score
        self.beam_width = beam_width

        self.traversal = TraversalEngine(
            guided_min_score=self.guided_traversal_min_score,
            beam_width=self.beam_width,
            min_entry_score=self.min_entry_score,
        )

        # in memory caches 
        self.nodes: dict[str, Node] = self.store.load_nodes(project_id)
        self.chunks: dict[str, Chunk] = self.store.load_chunks(project_id)
        self.documents: dict[str, Document] = self.store.load_documents(project_id)
        self.doc_checksums: set[str] = {
            d.checksum for d in self.documents.values()
        }

        self.out_edges: dict[str, list[Edge]] = defaultdict(list)
        self.in_edges: dict[str, list[Edge]] = defaultdict(list)
        self._load_edges_into_cache()

        # self.querying_matrix: np.ndarray | None = None
        # self.querying_ids: list[str] = []
        # self._rebuild_query_matrix()
        self._embedding_cache: dict[str, list[float]] = {}

    def _load_edges_into_cache(self):
        """Load this project's edges from dbinto directional caches."""
        self.out_edges.clear()
        self.in_edges.clear()
        for edge in self.store.load_edges(self.project_id):
            self.out_edges[edge.source_id].append(edge)
            self.in_edges[edge.target_id].append(edge)

    # ------------------------------------------
    # Document operations
    # ------------------------------------------

    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """
        Reads a file in binary chunks and computes its unique SHA-256 hash.
        Reads in chunks ensuring large files don't crash system memory.
        """
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            raise FileNotFoundError(f"Could not calculate checksum. File missing: {file_path}")
    
    def register_document(self, file_path: str, file_name: str) -> str | None:
        """
        Calculates file checksum, verifies duplicates, and registers the doc.
        Duplicate check is scoped to this project.
        """
        checksum = KnowledgeGraph.calculate_checksum(file_path)

        if checksum in self.doc_checksums:
            print(f"Skipping ingestion: Document '{file_name}' already exists in this project.")
            return None
        
        new_doc = Document(
            path=file_path,
            name=file_name,
            checksum=checksum,
            ingested_at=datetime.now(timezone.utc).isoformat(),
            project_id=self.project_id,
        )

        self.documents[new_doc.id] = new_doc
        self.doc_checksums.add(checksum)
        self.store.save_document(new_doc)
        
        return new_doc.id

    # ------------------------------------------
    # Chunk Operations
    # ------------------------------------------

    def add_chunk(self, chunk: Chunk) -> str:
        """Store a chunk and persist it."""
        self.chunks[chunk.id] = chunk
        self.store.save_chunk(chunk)
        return chunk.id

    def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Get a chunk by ID (from cache, fallback to sqlite)."""
        if chunk_id in self.chunks:
            return self.chunks[chunk_id]
        chunk = self.store.get_chunk(chunk_id)
        if chunk:
            self.chunks[chunk_id] = chunk
        return chunk

    def get_chunks_for_document(self, doc_id: str) -> list[Chunk]:
        """Get all chunks belonging to a document."""
        return [c for c in self.chunks.values() if c.document_id == doc_id]
    

    # ------------------------------------------
    # Node operations
    # ------------------------------------------

    def add_node(self, node: Node) -> str:
        """
        Adds a node to the graph, persists it, and updates the embedding matrix.
        """
        node.project_id = self.project_id
        self.nodes[node.id] = node
        self.store.save_node(node)
        text = f"{node.name} {node.description}".strip()
        emb = self.encoder.encode_single(text)
        self.vector_store.upsert_node_embedding(node.id, emb)
        self._embedding_cache[node.id] = emb
        return node.id

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def update_node_chunks(self, node_id: str, new_chunk_id: str) -> bool:
        """Add a new source chunk to an existing node (for dedup merges)."""
        node = self.nodes.get(node_id)
        if node is None:
            return False
        if new_chunk_id not in node.source_chunk_ids:
            node.source_chunk_ids.append(new_chunk_id)
            self.store.save_node(node)
        return True

    def get_nodes_by_type(self, node_type: str) -> list[Node]:
        """Filters nodes by type"""
        nt = node_type.upper()
        return [n for n in self.nodes.values() if n.node_type.upper() == nt]

    def delete_node(self, node_id: str) -> None:
        """Remove a node and all its edged from the graph."""
        if node_id not in self.nodes:
            return
        self.store.delete_node(node_id)
        del self.nodes[node_id]
        self._embedding_cache.pop(node_id, None)

        # Remove from adjacency caches
        self.out_edges.pop(node_id, None)
        self.in_edges.pop(node_id, None)
        for src, edges in self.out_edges.items():
            self.out_edges[src] = [e for e in edges if e.target_id != node_id]
        for tgt, edges in self.in_edges.items():
            self.in_edges[tgt] = [e for e in edges if e.source_id != node_id]

    # ------------------------------------------
    # Edge operations
    # ------------------------------------------
    
    def create_edge(self, edge: Edge) -> bool:
        """
        Add an edge to the graph. Returns True if new, False if duplicate.
        """
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            raise ValueError(
                f"Edge references non-existent node: {edge.source_id} -> {edge.target_id}"
            )

        if edge.source_id == edge.target_id:
            raise ValueError("Self-loops are not allowed")

        edge.project_id = self.project_id
        inserted = self.store.save_edge(edge)
        if inserted:
            self.out_edges[edge.source_id].append(edge)
            self.in_edges[edge.target_id].append(edge)
        return inserted

    def get_outgoing_edges(self, node_id: str) -> list[Edge]:
        """Get all edges where node+id is the source."""
        return list(self.out_edges.get(node_id, []))

    def get_incoming_edges(self, node_id: str) -> list[Edge]:
        """Get all edges where node_id is the target."""
        return list(self.in_edges.get(node_id, []))

    def get_all_edges(self, node_id: str) -> list[Edge]:
        """Get all edges connected to node_id (both directions)."""
        seen = set()
        result = []
        for e in self.out_edges.get(node_id, []) + self.in_edges.get(node_id, []):
            if e.id not in seen:
                seen.add(e.id)
                result.append(e)
        return result

    def get_edges_between(self, source_id: str, target_id: str) -> list[Edge]:
        """Get all direct edges from source to target."""
        return [e for e in self.out_edges.get(source_id, []) if e.target_id == target_id]

    def edge_exists(self, source_id: str, target_id: str, relation: str) -> bool:
        """Checks if a specific directed edge already exists."""
        for e in self.out_edges.get(source_id, []):
            if e.target_id == target_id and e.relation == relation:
                return True
        return False

    # ------------------------------------------------------------------
    # Retrieval: entry point search (via pg vector)
    # ------------------------------------------------------------------
    
    def get_top_k_nodes(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        """
        Find the k most semantically similar nodes to the query, scoped to
        this project.
        Returns list of (node_id, similarity_score) tuples, sorted descending.
        """
        query_emb = self.encoder.encode_single(query)
        return self.vector_store.search_nodes(query_emb, project_id=self.project_id, k=k)

    def search_chunks(self, query: str, k: int = 5) -> list[tuple[str, float]]:
        query_emb = self.encoder.encode_single(query)
        return self.vector_store.search_chunks(query_emb, project_id=self.project_id, k=k)

    def _get_node_embedding(self, node_id: str) -> list[float] | None:
        if node_id in self._embedding_cache:
            return self._embedding_cache[node_id]
        emb = self.vector_store.get_node_embedding(node_id)
        if emb:
            self._embedding_cache[node_id] = emb
        return emb

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def bfs_traversal(self, start_node_id: str, **kwargs) -> tuple[set[str], list[Edge]]:
        """
        BFS traversal from a starting node.

        Returns:
            visited: set of all node IDs reached
            path_edges: list of edges followed (in traversal order)
        """
        return self.traversal.bfs(
            start_node_id=start_node_id,
            nodes=self.nodes,
            out_edges=self.out_edges,
            in_edges=self.in_edges,
            **kwargs,
        )

    def guided_traversal(
        self,
        start_node_id: str,
        query: str,
        max_depth: int = 2,
        direction: str = "both",
    ) -> tuple[set[str], list[Edge], list[float]]:
        """
        Beam search traversal guided by query relevance.
        At each hop, only keep top-k most relevant neighbors.
        """
        query_emb = self.encoder.encode_single(query)

        return self.traversal.guided(
            start_node_id=start_node_id,
            query_emb=query_emb,
            nodes=self.nodes,
            out_edges=self.out_edges,
            in_edges=self.in_edges,
            get_embedding=self._get_node_embedding,
            max_depth=max_depth,
            direction=direction,
        )
    
    def multi_hop_query(
        self,
        question: str,
        top_k: int = 3,
        max_depth: int = 2,
        direction: str = "both",
        min_score: float | None = None,
    ) -> EvidencePath:
        """
        Delegate to TraversalEngine, passing graph state.

        `min_score`, when provided, overrides the instance-level
        `guided_traversal_min_score` for just this call — this is what lets
        the chat panel's "confidence threshold" dropdown tighten or loosen
        traversal per-question instead of only at construction time.
        """
        query_emb = self.encoder.encode_single(question)
        entry_nodes = self.get_top_k_nodes(question, k=top_k)

        return self.traversal.multi_hop(
            question=question,
            query_emb=query_emb,
            entry_nodes_with_scores=entry_nodes,
            nodes=self.nodes,
            out_edges=self.out_edges,
            in_edges=self.in_edges,
            get_embedding=self._get_node_embedding,
            search_chunks=lambda q, k: self.search_chunks(q, k),
            max_depth=max_depth,
            direction=direction,
            guided_min_score=min_score if min_score is not None else self.guided_traversal_min_score,
        )

    # ---------------------------------------------------------------------------
    # Graph metrics for analysis
    # ---------------------------------------------------------------------------
    def get_metrics(self) -> dict:
        """Computes basic graph statistics"""
        n_nodes = len(self.nodes)
        n_edges = sum(len(e) for e in self.out_edges.values())
        n_chunks = len(self.chunks)
        n_docs = len(self.documents)

        return {
            "node_count": n_nodes,
            "edge_count": n_edges,
            "chunk_count": n_chunks,
            "document_count": n_docs,
        }

    def get_central_nodes(self, top_k: int = 10) -> list[tuple[str, int]]:
        """Returns nodes sorted by total degree"""
        degrees = []
        for nid in self.nodes:
            deg = len(self.out_edges.get(nid, [])) + len(self.in_edges.get(nid, []))
            degrees.append((nid, deg))
        degrees.sort(key=lambda x: x[1], reverse=True)
        return degrees[:top_k]

    # ---------------------------------------------------------------------------
    # Evidence persistence
    # ---------------------------------------------------------------------------
    def save_evidence(self, evidence: EvidencePath) -> str:
        """Persist an evidence path and return its ID."""
        evidence.project_id = self.project_id
        return self.store.save_evidence(evidence)

    def get_past_evidence(self, question: str) -> list[EvidencePath]:
        """Retrieves previously saved evidence paths for a question, scoped to this project"""
        return self.store.load_evidence_for_question(question, project_id=self.project_id)

    def refresh(self) -> None:
        """Reload all in-memory caches from the database."""
        self.nodes = self.store.load_nodes(self.project_id)
        self.chunks = self.store.load_chunks(self.project_id)
        self.documents = self.store.load_documents(self.project_id)
        self.doc_checksums = {d.checksum for d in self.documents.values()}
        self._load_edges_into_cache()
        self._embedding_cache.clear()


    def export_to_json(self, output_dir: str = "graph_exports") -> dict:
        """Exoprt the entire knowledge graph to json files."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export nodes
        nodes_data = []
        for node_id, node in self.nodes.items():
            nodes_data.append({
                "id": node.id,
                "name": node.name,
                "node_type": node.node_type,
                "aliases": node.aliases,
                "description": node.description,
                "source_chunk_ids": node.source_chunk_ids,
                "created_at": node.created_at
            })

        # Export edges
        edges_data = []
        for edge_list in self.out_edges.values():
            for edge in edge_list:
                # Get node names for readability
                source_name = self.nodes.get(edge.source_id, Node(node_type="UNKNOWN", aliases=["UNKNOWN"], description="", source_chunk_ids=[])).name
                target_name = self.nodes.get(edge.target_id, Node(node_type="UNKNOWN", aliases=["UNKNOWN"], description="", source_chunk_ids=[])).name

                edges_data.append({
                    "id": edge.id,
                    "source_id": edge.source_id,
                    "source_name": source_name,
                    "target_id": edge.target_id,
                    "target_name": target_name,
                    "relation": edge.relation,
                    "source_chunk_id": edge.source_chunk_id,
                    "created_at": edge.created_at
                })

        # Export chunks
        chunks_data = []
        for chunk_id, chunk in self.chunks.items():
            chunks_data.append({
                "id": chunk.id,
                "text": chunk.text[:500] + "..." if len(chunk.text) > 500 else chunk.text,
                "full_text": chunk.text,
                "document_id": chunk.document_id,
                "index": chunk.index
            })

        # Export documents
        documents_data = []
        for doc_id, doc in self.documents.items():
            documents_data.append({
                "id": doc.id,
                "path": doc.path,
                "name": doc.name,
                "chunks": doc.chunks,
                "checksum": doc.checksum,
                "ingested_at": doc.ingested_at
            })

        # Combine everything
        graph_data = {
            "export_timestamp": timestamp,
            "metrics": self.get_metrics(),
            "nodes": nodes_data,
            "edges": edges_data,
            "chunks": chunks_data,
            "documents": documents_data
        }


        # Save main graph file
        graph_file = output_path / f"graph_export_{timestamp}.json"
        with open(graph_file, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)

        # Save separate file for each component
        with open(output_path / f"nodes_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(nodes_data, f, indent=2, ensure_ascii=False)

        with open(output_path / f"edges_{timestamp}.json", "w", encoding="utf-8") as f:
            json.dump(edges_data, f, indent=2, ensure_ascii=False)

        print(f"Graph exported to: {graph_file}")
        print(f"  - {len(nodes_data)} nodes")
        print(f"  - {len(edges_data)} edges")
        print(f"  - {len(chunks_data)} chunks")
        print(f"  - {len(documents_data)} documents")
        
        return {
            "graph_file": str(graph_file),
            "nodes_file": str(output_path / f"nodes_{timestamp}.json"),
            "edges_file": str(output_path / f"edges_{timestamp}.json"),
            "node_count": len(nodes_data),
            "edge_count": len(edges_data)
        }