import { X, FileText, Network } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface NodeData {
  id: string;
  label: string;
  type: string;
  description?: string;
  is_entry?: boolean;
}

interface NodePanelProps {
  node: NodeData | null;
  onClose: () => void;
}

export default function NodePanel({ node, onClose }: NodePanelProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.div
          initial={{ x: 320, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 320, opacity: 0 }}
          transition={{ type: "spring", damping: 30, stiffness: 300 }}
          className="absolute top-4 right-4 bottom-4 w-80 z-20 surface-raised flex flex-col overflow-hidden"
        >
          <div className="flex items-center justify-between p-4 border-b border-[var(--border-subtle)]">
            <div className="flex items-center gap-2">
              <Network className="w-4 h-4 text-[var(--accent)]" />
              <span className="text-xs font-medium uppercase tracking-widest text-[var(--text-tertiary)]">
                Entity
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-md text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-auto p-4 space-y-5">
            <div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)] leading-tight">
                {node.label}
              </h3>
              <div className="flex items-center gap-2 mt-2">
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--accent-glow)] text-[var(--accent)] border border-[var(--accent)]/20">
                  {node.type}
                </span>
                {node.is_entry && (
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    Entry Point
                  </span>
                )}
              </div>
            </div>

            {node.description && (
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)] mb-2">
                  Description
                </p>
                <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                  {node.description}
                </p>
              </div>
            )}

            <div>
              <p className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)] mb-2">
                ID
              </p>
              <code className="text-[11px] text-[var(--text-muted)] font-mono break-all">
                {node.id}
              </code>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}