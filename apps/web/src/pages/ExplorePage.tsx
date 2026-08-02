import { useCallback, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { useAuth } from "../lib/authContext";
import Header from "../components/Header";
import ResizableSplit from "../components/ResizableSplit";
import ChatPanel from "../components/ChatPanel";
import GraphViewer, { EvidencePath } from "../components/GraphViewer";
import NodePanel from "../components/NodePanel";
import IngestModal from "../components/IngestModal";

interface GraphNode {
  id: string;
  label: string;
  type: string;
  description?: string;
  is_entry?: boolean;
}
interface GraphEdge {
  id: string;
  source: string;
  target: string;
  label: string;
}

interface ExplorePageProps {
  projectId: string;
  onGoHome: () => void;
  onSelectProject: (id: string) => void;
}

export default function ExplorePage({ projectId, onGoHome, onSelectProject }: ExplorePageProps) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] });
  const [evidencePath, setEvidencePath] = useState<EvidencePath | null>(null);
  const [ingestOpen, setIngestOpen] = useState(false);

  // Reset the board whenever the active case changes
  useEffect(() => {
    setSelectedNodeId(null);
    setSelectedNode(null);
    setGraphData({ nodes: [], edges: [] });
    setEvidencePath(null);
  }, [projectId]);

  const { data: projects } = useQuery({
    queryKey: ["projects", user?.id ?? "anon"],
    queryFn: api.projects.list,
  });
  const activeProject = projects?.find((p) => p.id === projectId);

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["graph-metrics", projectId],
    queryFn: () => api.graph.metrics(projectId),
    refetchInterval: 15_000,
  });

  const { data: searchResults, isLoading: searching } = useQuery({
    queryKey: ["node-search", projectId, searchTerm],
    queryFn: () => api.graph.searchNodes(projectId, searchTerm, 10),
    enabled: searchTerm.length > 2,
  });

  const loadNodeNeighborhood = useCallback(
    async (nodeId: string) => {
      setSelectedNodeId(nodeId);
      setEvidencePath(null);

      const node = await api.graph.getNode(projectId, nodeId);
      setSelectedNode({ id: node.id, label: node.name, type: node.node_type, description: node.description });

      const traverse = await api.graph.traverse(projectId, nodeId, 2, "both");
      const nodes: GraphNode[] = [
        { id: node.id, label: node.name, type: node.node_type, description: node.description, is_entry: true },
      ];
      const edges: GraphEdge[] = [];
      const seen = new Set([node.id]);

      for (const e of traverse.edges) {
        for (const id of [e.source_id, e.target_id]) {
          if (seen.has(id)) continue;
          const n = await api.graph.getNode(projectId, id).catch(() => null);
          if (!n) continue;
          seen.add(id);
          nodes.push({ id: n.id, label: n.name, type: n.node_type, description: n.description });
        }
        edges.push({ id: e.id, source: e.source_id, target: e.target_id, label: e.relation });
      }

      setGraphData({ nodes, edges });
    },
    [projectId]
  );

  // When a chat answer completes, pull the evidence graph and light up the trail
  const handleEvidence = useCallback(
    async (evidenceId: string) => {
      try {
        const graph = await api.graph.evidenceGraph(projectId, evidenceId);
        const nodes: GraphNode[] = graph.nodes.map((n: any) => ({ ...n, is_entry: n.is_entry }));
        setGraphData({ nodes, edges: graph.edges });
        setEvidencePath({ nodeIds: nodes.map((n) => n.id), edgeIds: graph.edges.map((e: any) => e.id) });
        setSelectedNode(null);
        setSelectedNodeId(null);
      } catch {
        // evidence graph fetch failing shouldn't break the chat turn
      }
    },
    [projectId]
  );

  const refetchMetrics = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["graph-metrics", projectId] });
  }, [queryClient, projectId]);

  const canIngest = !!activeProject?.is_mine;

  return (
    <div className="flex flex-col h-screen bg-[var(--void)]">
      <Header
        projects={projects ?? []}
        activeProject={activeProject}
        onSelectProject={(id) => {
          if (id !== projectId) onSelectProject(id);
        }}
        onGoHome={onGoHome}
        metrics={
          metrics && {
            nodes: metrics.node_count,
            edges: metrics.edge_count,
            chunks: metrics.chunk_count,
            documents: metrics.document_count,
          }
        }
        metricsLoading={metricsLoading}
        onIngestClick={() => setIngestOpen(true)}
        canIngest={canIngest}
      />

      <div className="flex-1 min-h-0">
        <ResizableSplit
          left={<ChatPanel key={projectId} projectId={projectId} onEvidence={handleEvidence} />}
          right={
            <div className="relative w-full h-full p-3">
              <div className="absolute top-6 left-6 right-6 z-30">
                <div className="relative max-w-sm">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-faint)]" />
                  <input
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search entities to pin…"
                    className="w-full bg-[var(--panel)] border border-[var(--hairline)] rounded-md pl-9 pr-3 py-2 text-[12px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none focus:border-[var(--thread)] transition-colors"
                  />
                  {searching && <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--ink-faint)] animate-spin" />}

                  {searchTerm.length > 2 && searchResults && searchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1.5 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] overflow-hidden shadow-2xl">
                      {searchResults.map((n: any) => (
                        <button
                          key={n.id}
                          onClick={() => {
                            loadNodeNeighborhood(n.id);
                            setSearchTerm("");
                          }}
                          className="w-full text-left px-3 py-2 hover:bg-[var(--panel)] transition-colors border-b border-[var(--hairline)] last:border-0"
                        >
                          <p className="text-[13px] text-[var(--ink)]">{n.name}</p>
                          <p className="eyebrow mt-0.5">{n.node_type} · similarity {n.score}</p>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <GraphViewer
                nodes={graphData.nodes}
                edges={graphData.edges}
                onNodeSelect={(n) => {
                  setSelectedNode(n);
                  setSelectedNodeId(n?.id ?? null);
                }}
                selectedNodeId={selectedNodeId}
                evidencePath={evidencePath}
              />
              <NodePanel
                projectId={projectId}
                node={selectedNode}
                onClose={() => setSelectedNode(null)}
                onNavigateNode={loadNodeNeighborhood}
              />
            </div>
          }
        />
      </div>

      {canIngest && (
        <IngestModal projectId={projectId} open={ingestOpen} onClose={() => setIngestOpen(false)} onIngested={refetchMetrics} />
      )}
    </div>
  );
}
