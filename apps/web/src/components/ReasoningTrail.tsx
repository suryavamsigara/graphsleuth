import { useState } from "react";
import { ChevronRight, Search, Route, FileSearch, Sparkles, Save, AlertTriangle } from "lucide-react";
import { cn, formatMs, formatPct } from "../lib/utils";
import type { ReasoningStep } from "../lib/api";

const STEP_ICON: Record<string, any> = {
  search_nodes: Search,
  traverse_graph: Route,
  read_chunks: FileSearch,
  synthesize: Sparkles,
  save_trace: Save,
};

const STEP_LABEL: Record<string, string> = {
  search_nodes: "Located entry points",
  traverse_graph: "Traversed the graph",
  read_chunks: "Read source chunks",
  synthesize: "Synthesized answer",
  save_trace: "Filed trace path",
};

function summarizeOutput(step: ReasoningStep): string {
  const { action, output } = step;
  if (action === "search_nodes" && Array.isArray(output)) {
    return output
      .slice(0, 3)
      .map((n: any) => (Array.isArray(n) ? `${n[0]} (${(n[1] * 100).toFixed(0)}%)` : String(n)))
      .join(", ");
  }
  if (typeof output === "string") return output;
  if (output && typeof output === "object") {
    return Object.entries(output)
      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
      .join(" · ");
  }
  return String(output);
}

interface ReasoningTrailProps {
  steps: ReasoningStep[];
  confidence?: number;
  latencyMs?: number;
  live?: boolean; // still streaming
}

export default function ReasoningTrail({ steps, confidence, latencyMs, live }: ReasoningTrailProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 hover:bg-[var(--panel)] transition-colors"
      >
        <div className="flex items-center gap-2">
          <ChevronRight className={cn("w-3.5 h-3.5 text-[var(--ink-faint)] transition-transform", open && "rotate-90")} />
          <span className="eyebrow">Reasoning trail</span>
          <span className="mono text-[11px] text-[var(--ink-faint)]">{steps.length} steps</span>
        </div>

        <div className="flex items-center gap-2">
          {live && <span className="mono text-[10px] text-[var(--thread)] animate-pulse">tracing…</span>}
          {typeof latencyMs === "number" && (
            <span className="mono text-[10px] text-[var(--ink-faint)]">{formatMs(latencyMs)}</span>
          )}
          {typeof confidence === "number" && (
            <span
              className="stamp"
              style={{ color: confidence >= 0.6 ? "var(--verdict)" : confidence >= 0.35 ? "var(--thread)" : "var(--pin)" }}
            >
              {confidence < 0.35 && <AlertTriangle className="w-3 h-3" />}
              {formatPct(confidence)} confident
            </span>
          )}
        </div>
      </button>

      {open && (
        <div className="border-t border-[var(--hairline)] px-3 py-2 space-y-2">
          {steps.map((step) => {
            const Icon = STEP_ICON[step.action] ?? Sparkles;
            return (
              <div key={step.step} className="flex gap-2.5">
                <div className="flex flex-col items-center pt-0.5">
                  <div className="w-5 h-5 rounded-full border border-[var(--hairline-strong)] bg-[var(--panel)] flex items-center justify-center shrink-0">
                    <Icon className="w-2.5 h-2.5 text-[var(--thread)]" />
                  </div>
                  <div className="w-px flex-1 bg-[var(--hairline)] mt-1 last:hidden" />
                </div>
                <div className="pb-2 min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-[12px] font-medium text-[var(--ink)]">
                      Step {step.step} · {STEP_LABEL[step.action] ?? step.action}
                    </span>
                    <span className="mono text-[10px] text-[var(--ink-faint)]">{formatMs(step.latency_ms)}</span>
                  </div>
                  <p className="mono text-[11px] text-[var(--ink-dim)] leading-snug break-words mt-0.5">
                    {summarizeOutput(step)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
