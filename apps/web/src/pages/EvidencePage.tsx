import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Network, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { Link } from "react-router-dom";
import GraphViewer from "../components/GraphViewer";
import NodePanel from "../components/NodePanel";
import { useState, useCallback } from "react";

export default function EvidencePage() {
  const { id } = useParams<{ id: string }>();
  const [selectedNode, setSelectedNode] = useState<any>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["evidence-graph", id],
    queryFn: () => api.graph.evidenceGraph(id!),
    enabled: !!id,
  });

  const handleNodeSelect = useCallback((node: any) => {
    setSelectedNode(node);
  }, []);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-[var(--border-subtle)] px-6 py-3 flex items-center gap-3 bg-[var(--bg-base)] shrink-0">
        <Link
          to="/"
          className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex items-center gap-2">
          <Network className="w-4 h-4 text-[var(--accent)]" />
          <h2 className="text-[13px] font-semibold">Evidence Path</h2>
        </div>
        <code className="ml-auto text-[11px] text-[var(--text-muted)] font-mono bg-[var(--bg-surface)] px-2 py-0.5 rounded">
          {id?.slice(0, 8)}...
        </code>
      </div>

      <div className="flex-1 relative">
        {isLoading ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="flex items-center gap-2 text-[var(--text-muted)]">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-[12px]">Loading traversal graph...</span>
            </div>
          </div>
        ) : data ? (
          <>
            <GraphViewer
              nodes={data.nodes}
              edges={data.edges}
              onNodeSelect={handleNodeSelect}
            />
            <NodePanel node={selectedNode} onClose={() => setSelectedNode(null)} />
          </>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-[var(--text-muted)] text-[13px]">
            Evidence not found
          </div>
        )}
      </div>
    </div>
  );
}