import { useState, useRef, useEffect } from "react";
import { ChevronDown, FolderSearch } from "lucide-react";
import { cn } from "../lib/utils";

interface Workspace {
  id: string;
  name: string;
}

interface WorkspaceSwitcherProps {
  workspaces: Workspace[];
  activeId: string;
  onSelect: (id: string) => void;
}

export default function WorkspaceSwitcher({ workspaces, activeId, onSelect }: WorkspaceSwitcherProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const active = workspaces.find((w) => w.id === activeId) ?? workspaces[0];

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 pl-2.5 pr-2 py-1.5 rounded-md border border-[var(--hairline)] bg-[var(--panel)] hover:border-[var(--hairline-strong)] transition-colors"
      >
        <FolderSearch className="w-3.5 h-3.5 text-[var(--thread)]" />
        <div className="text-left leading-tight">
          <div className="eyebrow">Case File</div>
          <div className="text-[13px] font-medium text-[var(--ink)]">{active?.name ?? "—"}</div>
        </div>
        <ChevronDown className={cn("w-3.5 h-3.5 text-[var(--ink-faint)] transition-transform", open && "rotate-180")} />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1.5 w-64 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] shadow-2xl z-40 py-1">
          {workspaces.map((w) => (
            <button
              key={w.id}
              onClick={() => {
                onSelect(w.id);
                setOpen(false);
              }}
              className={cn(
                "w-full text-left px-3 py-2 text-[13px] hover:bg-[var(--panel)] transition-colors flex items-center justify-between",
                w.id === activeId ? "text-[var(--ink)]" : "text-[var(--ink-dim)]"
              )}
            >
              {w.name}
              {w.id === activeId && <span className="w-1.5 h-1.5 rounded-full bg-[var(--verdict)]" />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
