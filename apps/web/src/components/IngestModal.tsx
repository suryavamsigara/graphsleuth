import { useCallback, useRef, useState } from "react";
import { X, UploadCloud, FileText, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "../lib/utils";
import { api } from "../lib/api";

const ACCEPTED = [".pdf", ".txt", ".md", ".py"];

type FileStatus = "queued" | "uploading" | "done" | "error";

interface QueuedFile {
  id: string;
  file: File;
  status: FileStatus;
  error?: string;
  result?: { chunks_processed: number; nodes_created: number; edges_created: number };
}

interface IngestModalProps {
  projectId: string;
  open: boolean;
  onClose: () => void;
  onIngested: () => void; // refetch metrics/documents after a run
}

export default function IngestModal({ projectId, open, onClose, onIngested }: IngestModalProps) {
  const [files, setFiles] = useState<QueuedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((fileList: FileList | File[]) => {
    const accepted = Array.from(fileList).filter((f) =>
      ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setFiles((prev) => [
      ...prev,
      ...accepted.map((file) => ({ id: `${file.name}-${file.size}-${Date.now()}`, file, status: "queued" as FileStatus })),
    ]);
  }, []);

  const runUpload = useCallback(async () => {
    const pending = files.filter((f) => f.status === "queued");
    for (const qf of pending) {
      setFiles((prev) => prev.map((f) => (f.id === qf.id ? { ...f, status: "uploading" } : f)));
      try {
        const result = await api.documents.upload(projectId, qf.file);
        if (!result.success) throw new Error(result.error || "Ingestion failed");
        setFiles((prev) => prev.map((f) => (f.id === qf.id ? { ...f, status: "done", result } : f)));
      } catch (e: any) {
        setFiles((prev) => prev.map((f) => (f.id === qf.id ? { ...f, status: "error", error: String(e.message || e) } : f)));
      }
    }
    onIngested();
  }, [files, projectId, onIngested]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
      <motion.div
        initial={{ opacity: 0, y: 12, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 12, scale: 0.98 }}
        transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-lg rounded-lg border border-[var(--hairline)] bg-[var(--panel)] overflow-hidden"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--hairline)]">
          <div>
            <div className="eyebrow">Intake</div>
            <h2 className="text-[14px] font-medium text-[var(--ink)]">Add evidence to the case</h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-md text-[var(--ink-faint)] hover:text-[var(--ink)] hover:bg-[var(--panel-raised)]">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 space-y-3">
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragActive(false);
              addFiles(e.dataTransfer.files);
            }}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "rounded-md border-2 border-dashed px-6 py-8 flex flex-col items-center justify-center text-center cursor-pointer transition-colors",
              dragActive ? "border-[var(--thread)] bg-[var(--thread)]/5" : "border-[var(--hairline)] hover:border-[var(--hairline-strong)]"
            )}
          >
            <UploadCloud className={cn("w-6 h-6 mb-2", dragActive ? "text-[var(--thread)]" : "text-[var(--ink-faint)]")} />
            <p className="text-[13px] text-[var(--ink-dim)]">
              Drop files here, or <span className="text-[var(--thread)] font-medium">browse</span>
            </p>
            <p className="eyebrow mt-1.5">.pdf · .txt · .md · .py</p>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ACCEPTED.join(",")}
              className="hidden"
              onChange={(e) => e.target.files && addFiles(e.target.files)}
            />
          </div>

          {files.length > 0 && (
            <div className="max-h-56 overflow-auto space-y-1.5 pr-1">
              <AnimatePresence initial={false}>
                {files.map((qf) => (
                  <motion.div
                    key={qf.id}
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="flex items-center gap-2 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] px-3 py-2"
                  >
                    <FileText className="w-3.5 h-3.5 text-[var(--ink-faint)] shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-[12px] text-[var(--ink)] truncate">{qf.file.name}</p>
                      {qf.status === "done" && qf.result && (
                        <p className="eyebrow">
                          {qf.result.chunks_processed} chunks · {qf.result.nodes_created} nodes · {qf.result.edges_created} edges
                        </p>
                      )}
                      {qf.status === "error" && <p className="text-[11px] text-[var(--pin)]">{qf.error}</p>}
                    </div>
                    {qf.status === "queued" && <span className="eyebrow">Queued</span>}
                    {qf.status === "uploading" && <Loader2 className="w-3.5 h-3.5 text-[var(--thread)] animate-spin" />}
                    {qf.status === "done" && <CheckCircle2 className="w-3.5 h-3.5 text-[var(--verdict)]" />}
                    {qf.status === "error" && <XCircle className="w-3.5 h-3.5 text-[var(--pin)]" />}
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-[var(--hairline)]">
          <button onClick={onClose} className="px-3 py-1.5 text-[13px] text-[var(--ink-dim)] hover:text-[var(--ink)]">
            Close
          </button>
          <button
            onClick={runUpload}
            disabled={!files.some((f) => f.status === "queued")}
            className="px-3.5 py-1.5 rounded-md bg-[var(--thread)] text-[var(--void)] text-[13px] font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:brightness-110 transition-all"
          >
            Ingest {files.filter((f) => f.status === "queued").length || ""}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
