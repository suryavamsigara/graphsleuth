import { useState, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import GraphViewer from "../components/GraphViewer";
import NodePanel from "../components/NodePanel";

export default function ExplorePage() {
  const [query, setQuery] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({
    nodes: [],
    edges: [],
  });

  const { data: metrics } = useQuery({
    queryKey: ["graph-metrics"],
    queryFn: api.graph.metrics,
  });

  const { data: searchResults, isLoading: searching } = useQuery({
    queryKey: ["node-search", query],
    queryFn: () => api.graph.searchNodes(query, 10),
    enabled: query.length > 2,
  });

  const handleNodeSelect = useCallback((node: any) => {
    setSelectedNode(node);
    setSelectedNodeId(node?.id || null);
  }, []);

  const handleSearchSelect = useCallback(async (nodeId: string) => {
    setSelectedNodeId(nodeId);
    const node = await api.graph.getNode(nodeId);
    
    setSelectedNode({
      id: node.id,
      label: node.name,
      type: node.node_type,
      description: node.description,
    });

    const traverse = await api.graph.traverse(nodeId, 1, "both");
    
    const nodes: any[] = [
      {
        id: node.id,
        label: node.name,
        type: node.node_type,
        description: node.description,
      },
    ];
    const edges: any[] = [];

    for (const e of traverse.edges) {
      const src = await api.graph.getNode(e.source_id);
      const tgt = await api.graph.getNode(e.target_id);

      if (src && !nodes.find((n) => n.id === src.id)) {
        nodes.push({
          id: src.id,
          label: src.name,
          type: src.node_type,
          description: src.description,
        });
      }
      if (tgt && !nodes.find((n) => n.id === tgt.id)) {
        nodes.push({
          id: tgt.id,
          label: tgt.name,
          type: tgt.node_type,
          description: tgt.description,
        });
      }

      edges.push({
        id: e.id,
        source: e.source_id,
        target: e.target_id,
        label: e.relation,
      });
    }

    setGraphData({ nodes, edges });
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-[var(--border-subtle)] px-6 py-4 flex items-center justify-between bg-[var(--bg-base)] shrink-0">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Graph Explorer</h2>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
            {metrics
              ? `${metrics.node_count.toLocaleString()} nodes · ${metrics.edge_count.toLocaleString()} edges · ${metrics.document_count} documents`
              : "Loading metrics..."}
          </p>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search entities..."
            className="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg pl-9 pr-3 py-2 text-[12px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/30 transition-all"
          />
          {searching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)] animate-spin" />
          )}
        </div>
      </div>

      {query.length > 2 && searchResults && searchResults.length > 0 && (
        <div className="absolute top-16 left-6 right-6 z-30 max-w-md mx-auto">
          <div className="bg-[var(--bg-surface)] border border-[var(--border-visible)] rounded-xl overflow-hidden shadow-2xl">
            {searchResults.map((node: any) => (
              <button
                key={node.id}
                onClick={() => {
                  handleSearchSelect(node.id);
                  setQuery("");
                }}
                className="w-full text-left px-4 py-2.5 hover:bg-[var(--bg-hover)] transition-colors border-b border-[var(--border-subtle)] last:border-0"
              >
                <p className="text-[13px] font-medium text-[var(--text-primary)]">
                  {node.name}
                </p>
                <p className="text-[11px] text-[var(--text-tertiary)]">
                  {node.node_type} · similarity {node.score}
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="flex-1 relative min-h-0">
        <GraphViewer
          nodes={graphData.nodes}
          edges={graphData.edges}
          onNodeSelect={handleNodeSelect}
          selectedNodeId={selectedNodeId}
        />
        <NodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      </div>
    </div>
  );
}