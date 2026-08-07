import { useEffect, useState } from "react";
import { X, Network, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

interface NodeData {
  id: string;
  label: string;
  type: string;
  description?: string;
  is_entry?: boolean;
}

interface EdgeRow {
  id: string;
  source_id: string;
  source_name: string;
  target_id: string;
  target_name: string;
  relation: string;
}

interface NodePanelProps {
  projectId: string;
  node: NodeData | null;
  onClose: () => void;
  onNavigateNode?: (nodeId: string) => void; // clicking a connected entity in the edges table
}

export default function NodePanel({ projectId, node, onClose, onNavigateNode }: NodePanelProps) {
  const [aliases, setAliases] = useState<string[]>([]);
  const [edges, setEdges] = useState<EdgeRow[] | null>(null);
  const [chunks, setChunks] = useState<{ id: string; text: string }[] | null>(null);
  const [expandedChunk, setExpandedChunk] = useState<string | null>(null);
  const [loadingEdges, setLoadingEdges] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);

  useEffect(() => {
    if (!node) return;
    setEdges(null);
    setChunks(null);
    setExpandedChunk(null);

    let cancelled = false;

    setLoadingEdges(true);
    api.graph
      .getNode(projectId, node.id)
      .then((full) => {
        if (cancelled) return;
        setAliases(full.aliases ?? []);
        // fetch each source chunk lazily, collapsed by default
        setLoadingChunks(true);
        Promise.all(
          (full.source_chunk_ids ?? []).slice(0, 20).map((cid: string) => api.graph.getChunk(projectId, cid).catch(() => null))
        ).then((results) => {
          if (cancelled) return;
          setChunks(results.filter(Boolean) as { id: string; text: string }[]);
          setLoadingChunks(false);
        });
      })
      .catch(() => {});

    api.graph
      .getNodeEdges(projectId, node.id)
      .then((rows) => !cancelled && setEdges(rows))
      .catch(() => !cancelled && setEdges([]))
      .finally(() => !cancelled && setLoadingEdges(false));

    return () => {
      cancelled = true;
    };
  }, [projectId, node?.id]);

  return (
    <AnimatePresence>
      {node && (
        <motion.div
          initial={{ x: 340, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 340, opacity: 0 }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
          className="absolute top-4 right-4 bottom-4 w-[22rem] z-40 rounded-lg border border-[var(--hairline)] bg-[var(--panel)] flex flex-col overflow-hidden shadow-2xl"
        >
          {/* manila folder tab */}
          <div className="flex items-center justify-between px-4 pt-3 pb-2.5 border-b border-[var(--hairline)]">
            <div className="flex items-center gap-2">
              <Network className="w-3.5 h-3.5 text-[var(--thread)]" />
              <span className="eyebrow">Node · Entity</span>
            </div>
            <button onClick={onClose} className="p-1 rounded-md text-[var(--ink-faint)] hover:text-[var(--ink)] hover:bg-[var(--panel-raised)] transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-auto px-4 py-3.5 space-y-5">
            <div>
              <h3 className="text-[16px] font-semibold text-[var(--ink)] leading-tight">{node.label}</h3>
              <div className="flex items-center flex-wrap gap-1.5 mt-2">
                <span className="stamp" style={{ color: "var(--wire)" }}>{node.type}</span>
                {node.is_entry && (
                  <span className="stamp" style={{ color: "var(--pin)" }}>Entry point</span>
                )}
              </div>
            </div>

            {aliases.length > 1 && (
              <section>
                <p className="eyebrow mb-1.5">Also known as</p>
                <div className="flex flex-wrap gap-1.5">
                  {aliases.slice(1).map((a) => (
                    <span key={a} className="mono text-[11px] px-2 py-0.5 rounded bg-[var(--panel-raised)] border border-[var(--hairline)] text-[var(--ink-dim)]">
                      {a}
                    </span>
                  ))}
                </div>
              </section>
            )}

            {node.description && (
              <section>
                <p className="eyebrow mb-1.5">Summary</p>
                <p className="text-[13px] text-[var(--ink-dim)] leading-relaxed">{node.description}</p>
              </section>
            )}

            <section>
              <p className="eyebrow mb-1.5">
                Connected edges {edges && <span className="text-[var(--ink-faint)]">({edges.length})</span>}
              </p>
              {loadingEdges && <p className="text-[12px] text-[var(--ink-faint)]">Reading the file…</p>}
              {edges && edges.length === 0 && <p className="text-[12px] text-[var(--ink-faint)]">No relations recorded.</p>}
              {edges && edges.length > 0 && (
                <div className="rounded-md border border-[var(--hairline)] overflow-hidden">
                  {edges.map((e, i) => {
                    const isSource = e.source_id === node.id;
                    const other = isSource ? e.target_name : e.source_name;
                    const otherId = isSource ? e.target_id : e.source_id;
                    return (
                      <button
                        key={e.id}
                        onClick={() => onNavigateNode?.(otherId)}
                        className={cn(
                          "w-full text-left px-2.5 py-2 flex items-center gap-1.5 hover:bg-[var(--panel-raised)] transition-colors",
                          i !== 0 && "border-t border-[var(--hairline)]"
                        )}
                      >
                        <span className="mono text-[11px] text-[var(--ink-faint)] shrink-0">
                          {isSource ? "→" : "←"}
                        </span>
                        <span className="mono text-[11px] text-[var(--thread)] shrink-0">{e.relation}</span>
                        <span className="text-[12px] text-[var(--ink)] truncate">{other}</span>
                      </button>
                    );
                  })}
                </div>
              )}
            </section>

            <section>
              <p className="eyebrow mb-1.5">
                Source chunks {chunks && <span className="text-[var(--ink-faint)]">({chunks.length})</span>}
              </p>
              {loadingChunks && <p className="text-[12px] text-[var(--ink-faint)]">Pulling exhibits…</p>}
              <div className="space-y-1.5">
                {chunks?.map((c, i) => {
                  const isOpen = expandedChunk === c.id;
                  return (
                    <div key={c.id} className="exhibit">
                      <button
                        onClick={() => setExpandedChunk(isOpen ? null : c.id)}
                        className="w-full flex items-center justify-between px-2.5 py-1.5"
                      >
                        <span className="mono text-[10px] text-[var(--ink-faint)] uppercase tracking-wide">
                          Exhibit {String.fromCharCode(65 + i)}
                        </span>
                        <ChevronRight className={cn("w-3 h-3 text-[var(--ink-faint)] transition-transform", isOpen && "rotate-90")} />
                      </button>
                      {isOpen && (
                        <p className="px-2.5 pb-2 text-[12px] text-[var(--ink-dim)] leading-relaxed whitespace-pre-wrap">
                          {c.text}
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            <section>
              <p className="eyebrow mb-1">Node ID</p>
              <code className="mono text-[11px] text-[var(--ink-faint)] break-all">{node.id}</code>
            </section>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
