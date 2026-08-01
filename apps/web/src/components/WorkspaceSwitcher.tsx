import { useState, useRef, useEffect } from "react";
import { ChevronDown, FolderSearch, Home, Lock, Globe } from "lucide-react";
import { ProjectSummary } from "../lib/api";
import { cn } from "../lib/utils";

interface WorkspaceSwitcherProps {
  projects: ProjectSummary[];
  active: ProjectSummary | undefined;
  onSelect: (id: string) => void;
  onGoHome: () => void;
}

export default function WorkspaceSwitcher({ projects, active, onSelect, onGoHome }: WorkspaceSwitcherProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const mine = projects.filter((p) => p.is_mine);
  const others = projects.filter((p) => !p.is_mine);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 pl-2.5 pr-2 py-1.5 rounded-md border border-[var(--hairline)] bg-[var(--panel)] hover:border-[var(--hairline-strong)] transition-colors"
      >
        <FolderSearch className="w-3.5 h-3.5 text-[var(--thread)]" />
        <div className="text-left leading-tight">
          <div className="eyebrow">Case File</div>
          <div className="text-[13px] font-medium text-[var(--ink)] max-w-[16ch] truncate">{active?.name ?? "—"}</div>
        </div>
        <ChevronDown className={cn("w-3.5 h-3.5 text-[var(--ink-faint)] transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-72 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] shadow-2xl z-40 py-1 max-h-80 overflow-auto">
          <button
            onClick={() => {
              onGoHome();
              setOpen(false);
            }}
            className="w-full text-left px-3 py-2 text-[13px] text-[var(--ink-dim)] hover:bg-[var(--panel)] transition-colors flex items-center gap-2 border-b border-[var(--hairline)]"
          >
            <Home className="w-3.5 h-3.5" />
            All cases
          </button>

          {mine.length > 0 && (
            <div className="px-3 pt-2 pb-1 eyebrow">Mine</div>
          )}
          {mine.map((p) => (
            <ProjectRow key={p.id} project={p} active={p.id === active?.id} onSelect={() => { onSelect(p.id); setOpen(false); }} />
          ))}

          {others.length > 0 && (
            <div className="px-3 pt-2 pb-1 eyebrow">Public</div>
          )}
          {others.map((p) => (
            <ProjectRow key={p.id} project={p} active={p.id === active?.id} onSelect={() => { onSelect(p.id); setOpen(false); }} />
          ))}
        </div>
      )}
    </div>
  );
}

function ProjectRow({ project, active, onSelect }: { project: ProjectSummary; active: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full text-left px-3 py-2 text-[13px] hover:bg-[var(--panel)] transition-colors flex items-center justify-between gap-2",
        active ? "text-[var(--ink)]" : "text-[var(--ink-dim)]"
      )}
    >
      <span className="truncate">{project.name}</span>
      <span className="flex items-center gap-1.5 shrink-0">
        {project.is_public ? <Globe className="w-3 h-3 text-[var(--ink-faint)]" /> : <Lock className="w-3 h-3 text-[var(--ink-faint)]" />}
        {active && <span className="w-1.5 h-1.5 rounded-full bg-[var(--verdict)]" />}
      </span>
    </button>
  );
}
