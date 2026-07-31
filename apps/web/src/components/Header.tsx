import { Plus } from "lucide-react";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import MetricsPill from "./MetricsPill";

interface Workspace {
  id: string;
  name: string;
}

interface HeaderProps {
  workspaces: Workspace[];
  activeWorkspaceId: string;
  onSelectWorkspace: (id: string) => void;
  metrics: { nodes: number; edges: number; chunks: number; documents: number } | undefined;
  metricsLoading?: boolean;
  onIngestClick: () => void;
}

export default function Header({
  workspaces,
  activeWorkspaceId,
  onSelectWorkspace,
  metrics,
  metricsLoading,
  onIngestClick,
}: HeaderProps) {
  return (
    <header className="h-14 shrink-0 flex items-center justify-between gap-3 px-4 border-b border-[var(--hairline)] bg-[var(--void)]">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 pr-3 mr-1 border-r border-[var(--hairline)]">
          <div className="w-6 h-6 rounded-[3px] bg-[var(--thread)] flex items-center justify-center rotate-[-3deg]">
            <span className="mono text-[11px] font-bold text-[var(--void)]">GS</span>
          </div>
          <span className="mono text-[13px] font-semibold tracking-tight text-[var(--ink)]">GraphSleuth</span>
        </div>

        <WorkspaceSwitcher
          workspaces={workspaces}
          activeId={activeWorkspaceId}
          onSelect={onSelectWorkspace}
        />
      </div>

      <div className="flex items-center gap-3">
        <MetricsPill
          nodes={metrics?.nodes ?? 0}
          edges={metrics?.edges ?? 0}
          chunks={metrics?.chunks ?? 0}
          documents={metrics?.documents ?? 0}
          loading={metricsLoading}
        />

        <button
          onClick={onIngestClick}
          className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 rounded-md bg-[var(--thread)] text-[var(--void)] text-[13px] font-medium hover:brightness-110 active:brightness-95 transition-all"
        >
          <Plus className="w-3.5 h-3.5" strokeWidth={2.5} />
          Add Document
        </button>
      </div>
    </header>
  );
}
