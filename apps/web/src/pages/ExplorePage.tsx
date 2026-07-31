import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

export default function ExplorePage() {
  const [query, setQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const { data: metrics } = useQuery({
    queryKey: ["graph-metrics"],
    queryFn: api.graph.metrics,
  });

  const { data: searchResults, isLoading: searching } = useQuery({
    queryKey: ["node-search", query],
    queryFn: () => api.graph.searchNodes(query, 10),
    enabled: query.length > 2,
  });

  const { data: nodeDetail } = useQuery({
    queryKey: ["node-detail", selectedNode],
    queryFn: () => api.graph.getNode(selectedNode!),
    enabled: !!selectedNode,
  });

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Explore Graph</h2>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {metrics && (
          <>
            <StatCard label="Nodes" value={metrics.node_count} />
            <StatCard label="Edges" value={metrics.edge_count} />
            <StatCard label="Documents" value={metrics.document_count} />
          </>
        )}
      </div>

      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search entities..."
          className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-10 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
        />
      </div>

      {searching && (
        <div className="flex items-center gap-2 text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          Searching...
        </div>
      )}

      {searchResults && searchResults.length > 0 && (
        <div className="grid grid-cols-2 gap-3 mb-6">
          {searchResults.map((node: any) => (
            <button
              key={node.id}
              onClick={() => setSelectedNode(node.id)}
              className={cn(
                "text-left p-3 rounded-lg border transition-colors",
                selectedNode === node.id
                  ? "bg-emerald-900/20 border-emerald-700"
                  : "bg-slate-800 border-slate-700 hover:border-slate-500"
              )}
            >
              <p className="font-medium text-sm">{node.name}</p>
              <p className="text-xs text-slate-400">
                {node.node_type} · score {node.score}
              </p>
            </button>
          ))}
        </div>
      )}

      {nodeDetail && (
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
          <h3 className="font-bold text-lg mb-2">{nodeDetail.name}</h3>
          <p className="text-sm text-slate-300 mb-3">{nodeDetail.description}</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {nodeDetail.aliases.map((a: string) => (
              <span key={a} className="text-xs bg-slate-700 px-2 py-1 rounded">
                {a}
              </span>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            {nodeDetail.source_chunk_ids.length} source chunks
          </p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
      <p className="text-2xl font-bold text-emerald-400">{value}</p>
      <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
    </div>
  );
}