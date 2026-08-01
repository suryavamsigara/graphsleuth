import { Plus } from "lucide-react";
import WorkspaceSwitcher from "./WorkspaceSwitcher";
import MetricsPill from "./MetricsPill";
import SignInWidget from "./SignInWidget";
import { ProjectSummary } from "../lib/api";

interface HeaderProps {
  projects: ProjectSummary[];
  activeProject: ProjectSummary | undefined;
  onSelectProject: (id: string) => void;
  onGoHome: () => void;
  metrics: { nodes: number; edges: number; chunks: number; documents: number } | undefined;
  metricsLoading?: boolean;
  onIngestClick: () => void;
  canIngest: boolean;
}

export default function Header({
  projects,
  activeProject,
  onSelectProject,
  onGoHome,
  metrics,
  metricsLoading,
  onIngestClick,
  canIngest,
}: HeaderProps) {
  return (
    <header className="h-14 shrink-0 flex items-center justify-between gap-3 px-4 border-b border-[var(--hairline)] bg-[var(--void)]">
      <div className="flex items-center gap-3 min-w-0">
        <button onClick={onGoHome} className="flex items-center gap-2 pr-3 mr-1 border-r border-[var(--hairline)] shrink-0">
          <div className="w-6 h-6 rounded-[3px] bg-[var(--thread)] flex items-center justify-center rotate-[-3deg]">
            <span className="mono text-[11px] font-bold text-[var(--void)]">GS</span>
          </div>
          <span className="mono text-[13px] font-semibold tracking-tight text-[var(--ink)]">GraphSleuth</span>
        </button>

        <WorkspaceSwitcher projects={projects} active={activeProject} onSelect={onSelectProject} onGoHome={onGoHome} />
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <MetricsPill
          nodes={metrics?.nodes ?? 0}
          edges={metrics?.edges ?? 0}
          chunks={metrics?.chunks ?? 0}
          documents={metrics?.documents ?? 0}
          loading={metricsLoading}
        />

        {canIngest && (
          <button
            onClick={onIngestClick}
            className="flex items-center gap-1.5 pl-2.5 pr-3 py-1.5 rounded-md bg-[var(--thread)] text-[var(--void)] text-[13px] font-medium hover:brightness-110 active:brightness-95 transition-all"
          >
            <Plus className="w-3.5 h-3.5" strokeWidth={2.5} />
            Add Document
          </button>
        )}

        <SignInWidget />
      </div>
    </header>
  );
}
