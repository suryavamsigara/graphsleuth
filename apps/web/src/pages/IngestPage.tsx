import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2, FileCode, FileType } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";

interface UploadResult {
  file: string;
  status: "success" | "error" | "duplicate";
  docId?: string;
  chunks?: number;
  nodes?: number;
  edges?: number;
  error?: string;
}

function FileIcon({ name }: { name: string }) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return <FileType className="w-4 h-4 text-red-400" />;
  if (ext === "py") return <FileCode className="w-4 h-4 text-blue-400" />;
  return <FileText className="w-4 h-4 text-[var(--text-tertiary)]" />;
}

export default function IngestPage() {
  const [uploads, setUploads] = useState<UploadResult[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    setIsUploading(true);
    for (const file of acceptedFiles) {
      const result = await api.documents.upload(file);
      setUploads((prev) => [
        ...prev,
        {
          file: file.name,
          status: result.success
            ? result.error?.includes("Duplicate")
              ? "duplicate"
              : "success"
            : "error",
          docId: result.document_id,
          chunks: result.chunks_processed,
          nodes: result.nodes_created,
          edges: result.edges_created,
          error: result.error,
        },
      ]);
    }
    setIsUploading(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/plain": [".txt", ".md"],
      "text/x-python": [".py"],
      "application/pdf": [".pdf"],
    },
  });

  return (
    <div className="h-full overflow-auto p-8 max-w-2xl mx-auto">
      <div className="mb-8">
        <h2 className="text-xl font-semibold tracking-tight">Ingest Documents</h2>
        <p className="text-[13px] text-[var(--text-tertiary)] mt-1">
          Upload files to extract entities and build the knowledge graph.
        </p>
      </div>

      <div
        {...getRootProps()}
        className={cn(
          "relative border border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300",
          isDragActive
            ? "border-[var(--accent)]/40 bg-[var(--accent)]/5"
            : "border-[var(--border-visible)] bg-[var(--bg-surface)] hover:border-[var(--text-muted)] hover:bg-[var(--bg-raised)]"
        )}
      >
        <input {...getInputProps()} />
        <div
          className={cn(
            "w-12 h-12 rounded-xl mx-auto mb-4 flex items-center justify-center transition-colors",
            isDragActive ? "bg-[var(--accent)]/10" : "bg-[var(--bg-raised)]"
          )}
        >
          <Upload
            className={cn(
              "w-5 h-5 transition-colors",
              isDragActive ? "text-[var(--accent)]" : "text-[var(--text-muted)]"
            )}
          />
        </div>
        <p className="text-[13px] font-medium text-[var(--text-primary)]">
          {isDragActive ? "Drop files here" : "Drag files here or click to browse"}
        </p>
        <p className="text-[11px] text-[var(--text-muted)] mt-2">
          Supports TXT, MD, PY, PDF
        </p>
      </div>

      {isUploading && (
        <div className="mt-6 flex items-center gap-2 text-[var(--accent)]">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span className="text-[12px] font-medium">Processing documents...</span>
        </div>
      )}

      {uploads.length > 0 && (
        <div className="mt-8 space-y-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-widest text-[var(--text-muted)] mb-3">
            Upload History
          </h3>
          {uploads.map((u, i) => (
            <div
              key={i}
              className="flex items-center gap-3 bg-[var(--bg-surface)] rounded-xl p-3 border border-[var(--border-subtle)]"
            >
              <div className="w-8 h-8 rounded-lg bg-[var(--bg-raised)] flex items-center justify-center shrink-0">
                <FileIcon name={u.file} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[13px] font-medium text-[var(--text-primary)] truncate">
                  {u.file}
                </p>
                <p className="text-[11px] text-[var(--text-tertiary)]">
                  {u.status === "success" && (
                    <span className="tabular-nums">
                      {u.chunks} chunks · {u.nodes} nodes · {u.edges} edges
                    </span>
                  )}
                  {u.status === "duplicate" && "Already ingested"}
                  {u.status === "error" && (
                    <span className="text-red-400">{u.error}</span>
                  )}
                </p>
              </div>
              <div className="shrink-0">
                {u.status === "success" && (
                  <CheckCircle className="w-4 h-4 text-[var(--accent)]" />
                )}
                {u.status === "duplicate" && (
                  <AlertCircle className="w-4 h-4 text-amber-400" />
                )}
                {u.status === "error" && (
                  <AlertCircle className="w-4 h-4 text-red-400" />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}