import { useState } from "react";
import { X, Loader2 } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

interface NewCaseModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: (projectId: string) => void;
}

export default function NewCaseModal({ open, onClose, onCreated }: NewCaseModalProps) {
  const [name, setName] = useState("");
  const [isPublic, setIsPublic] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const project = await api.projects.create(name.trim(), isPublic);
      onCreated(project.id);
      setName("");
      setIsPublic(false);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <div className="w-full max-w-sm rounded-lg border border-[var(--hairline)] bg-[var(--panel)] overflow-hidden">
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--hairline)]">
          <div>
            <div className="eyebrow">New case</div>
            <h2 className="text-[14px] font-medium text-[var(--ink)]">Open a case file</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-[var(--ink-faint)] hover:text-[var(--ink)] hover:bg-[var(--panel-raised)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div>
            <label className="eyebrow block mb-1.5">Case name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && create()}
              placeholder="e.g. Q3 Contract Review"
              autoFocus
              className="w-full bg-[var(--panel-raised)] border border-[var(--hairline)] rounded-md px-3 py-2 text-[13px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none focus:border-[var(--thread)]"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => setIsPublic(e.target.checked)}
              className="accent-[var(--thread)]"
            />
            <span className="text-[12px] text-[var(--ink-dim)]">
              Make this case public <span className="text-[var(--ink-faint)]">— anyone can explore and ask questions</span>
            </span>
          </label>

          {error && <p className="text-[12px] text-[var(--pin)]">{error}</p>}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-[var(--hairline)]">
          <button onClick={onClose} className="px-3 py-1.5 text-[13px] text-[var(--ink-dim)] hover:text-[var(--ink)]">
            Cancel
          </button>
          <button
            onClick={create}
            disabled={busy || !name.trim()}
            className={cn(
              "px-3.5 py-1.5 rounded-md text-[13px] font-medium transition-all flex items-center gap-1.5",
              busy || !name.trim() ? "bg-[var(--hairline)] text-[var(--ink-faint)]" : "bg-[var(--thread)] text-[var(--void)] hover:brightness-110"
            )}
          >
            {busy && <Loader2 className="w-3 h-3 animate-spin" />}
            Open case
          </button>
        </div>
      </div>
    </div>
  );
}
