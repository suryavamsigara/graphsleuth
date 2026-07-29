import numpy as np
from collections import deque
from model2vec import StaticModel
from sklearn.metrics.pairwise import cosine_similarity

from engine.models.edge import Edge
from engine.models.document import EvidencePath


class TraversalEngine:
    "Traversal algorithms"
    def __init__(self, querying_model):
        self.querying_model: StaticModel = querying_model

    def bfs(
        self,
        start_node_id: str,
        nodes: dict,
        out_edges: dict,
        in_edges: dict,
        max_depth: int = 2,
        direction: str = "both", # out, in, both
        relation_filter: str | None = None,
        node_type_filter: str | None = None,
    ) -> tuple[set[str], list[Edge]]:
        """
        BFS traversal from a starting node.

        Returns:
            visited: set of all node IDs reached
            path_edges: list of edges followed (in traversal order)
        """
        if start_node_id not in nodes:
            return set(), []

        visited = {start_node_id}
        queue = deque([(start_node_id, 0)])
        path_edges: list[Edge] = []

        while queue:
            current_id, depth = queue.popleft()
            if depth >= max_depth:
                continue

            # Collect edges based on direction
            edges_to_follow: list[Edge] = []
            if direction in ("out", "both"):
                edges_to_follow.extend(out_edges.get(current_id, []))
            if direction in ("in", "both"):
                edges_to_follow.extend(in_edges.get(current_id, []))

            for edge in edges_to_follow:
                # Determine neibhour
                if edge.source_id == current_id:
                    neighbor_id = edge.target_id
                else:
                    neighbor_id = edge.source_id

                if relation_filter and edge.relation != relation_filter:
                    continue
                if node_type_filter:
                    neighbor = nodes.get(neighbor_id)
                    if neighbor and neighbor.node_type.upper() != node_type_filter.upper():
                        continue

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    path_edges.append(edge)
                    queue.append((neighbor_id, depth + 1))

        return visited, path_edges


    def guided(
        self,
        start_node_id: str,
        query: str,
        nodes: dict,
        out_edges: dict,
        in_edges: dict,
        max_depth: int = 2,
        beam_width: int = 3,
        direction: str = "both",
        min_score: float = 0.20,
    ) -> tuple[set[str], list[Edge], list[float]]:
        """
        Beam search traversal guided by query relevance.
        At each hop, only keep top-k most relevant neighbors.
        """
        if start_node_id not in nodes:
            return set(), [], []

        # Score a node by query embedding similarity
        def score_node(node_id: str) -> float:
            node = nodes.get(node_id)
            if not node:
                return 0.0
            text = f"{node.name} {node.description} {node.node_type}"
            emb = self.querying_model.encode(text).reshape(1, -1)
            query_emb = self.querying_model.encode(query).reshape(1, -1)
            return float(cosine_similarity(query_emb, emb)[0][0])

        visited = {start_node_id}
        path_edges = []
        scores = [score_node(start_node_id)]

        # beam = list of (node_id, path_edges_to_here, cumulative_score)
        beam = [(start_node_id, [], score_node(start_node_id))]

        for depth in range(max_depth):
            candidates = []

            for current_id, edges_so_far, cum_score in beam:
                # Get neighbours
                neighbors = []
                if direction in ("out", "both"):
                    for e in out_edges.get(current_id, []):
                        neighbors.append((e.target_id, e))
                if direction in ("in", "both"):
                    for e in in_edges.get(current_id, []):
                        neighbors.append((e.source_id, e))

                for neighbor_id, edge in neighbors:
                    if neighbor_id in visited:
                        continue

                    neighbor_score = score_node(neighbor_id)
                    if neighbor_score < min_score:
                        continue

                    new_edges = edges_so_far + [edge]
                    new_score = cum_score + neighbor_score
                    candidates.append((neighbor_id, new_edges, new_score))
                    visited.add(neighbor_id)

            if not candidates:
                break

            # Keep top beam_width candidates
            candidates.sort(key=lambda x: x[2], reverse=True)
            beam = candidates[:beam_width]
            path_edges.extend([e for _, edges, _ in beam for e in edges])
            scores.extend([s for _, _, s in beam])
        return visited, path_edges, scores


    def multi_hop(
        self,
        question: str,
        entry_nodes_with_scores: list[tuple[str, float]],
        nodes: dict,
        out_edges: dict,
        in_edges: dict,
        chunks: dict,
        max_depth: int = 2,
        direction: str = "both",
        min_entry_score: float = 0.35,
        beam_width: int = 3,
        guided_min_score: float = 0.20,
    ) -> EvidencePath:
        """
        The main query interface.
        1. Find entry nodes via embedding similarity
        2. Traverse graph from each entry point
        3. Collect all reachable nodes, edges, and source chunks
        4. Return an EvidencePath
        """

        valid_entries = [(nid, score) for nid, score in entry_nodes_with_scores if score >= min_entry_score]
        print("Valid: ", valid_entries)

        if not valid_entries:
            chunk_results = self._search_chunks(question, chunks)
            if chunk_results:
                return EvidencePath(
                    question=question,
                    entry_nodes=[],
                    visited_nodes=[],
                    traversed_edges=[],
                    source_chunks=[cid for cid, _ in chunk_results],
                    confidence=round(sum(score for _, score in chunk_results) / len(chunk_results), 4),
                )

            return EvidencePath(
                question=question,
                entry_nodes=[],
                visited_nodes=[],
                traversed_edges=[],
                source_chunks=[],
                confidence=0.0,
            )
        entry_node_ids = [nid for nid, _ in valid_entries]

        all_visited: set[str] = set()
        all_edges: list[Edge] = []

        for start_id in entry_node_ids:
            visited, edges, _ = self.guided(
                start_node_id=start_id,
                query=question,
                nodes=nodes,
                out_edges=out_edges,
                in_edges=in_edges,
                max_depth=max_depth,
                direction=direction,
                beam_width=beam_width,
                min_score=guided_min_score,
            )
            all_visited.update(visited)
            all_edges.extend(edges)

        # Collect source chuks from all visited nodes
        all_chunk_ids: set[str] = set()
        for node_id in all_visited:
            node = nodes.get(node_id)
            if node:
                all_chunk_ids.update(node.source_chunk_ids)

        # Deduplicate edges while preserving order
        seen_edge_ids = set()
        unique_edges = []
        for e in all_edges:
            if e.id not in seen_edge_ids:
                seen_edge_ids.add(e.id)
                unique_edges.append(e)
                all_chunk_ids.add(e.source_chunk_id)

        # Confidence = average similarity of entry nodes
        avg_confidence = (
            sum(score for _, score in valid_entries) / len(valid_entries) if valid_entries else 0.0
        )

        return EvidencePath(
            question=question,
            entry_nodes=entry_node_ids,
            visited_nodes=list(all_visited),
            traversed_edges=unique_edges,
            source_chunks=list(all_chunk_ids),
            confidence=round(avg_confidence, 4),
        )

    def _search_chunks(
        self,
        query: str,
        chunks: dict,
        k: int = 5,
    ) -> list[tuple[str, float]]:
        if not chunks:
            return []

        query_emb = self.querying_model.encode(query).reshape(1, -1)
        texts, ids = [], []
        for cid, chunk in chunks.items():
            texts.append(chunk.text)
            ids.append(cid)

        if not texts:
            return []

        embs = self.querying_model.encode(texts)
        sims = cosine_similarity(query_emb, np.vstack(embs))[0]
        actual_k = min(k, len(ids))
        top_indices = sims.argsort()[::-1][:actual_k]
        return [(ids[idx], float(sims[idx])) for idx in top_indices]