import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
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

export default function IngestPage() {
  const [uploads, setUploads] = useState<UploadResult[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
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
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "text/plain": [".txt", ".md"],
      "text/x-python": [".py"],
      "application/pdf": [".pdf"],
    },
  });

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">Ingest Documents</h2>

      <div
        {...getRootProps()}
        className={cn(
          "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors",
          isDragActive
            ? "border-emerald-500 bg-emerald-900/10"
            : "border-slate-700 hover:border-slate-500"
        )}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 mx-auto mb-4 text-slate-400" />
        <p className="text-lg font-medium">
          {isDragActive ? "Drop files here..." : "Drag & drop files here"}
        </p>
        <p className="text-sm text-slate-500 mt-2">
          Supports .txt, .md, .py, .pdf
        </p>
      </div>

      {isUploading && (
        <div className="mt-6 flex items-center gap-2 text-emerald-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Processing...</span>
        </div>
      )}

      {uploads.length > 0 && (
        <div className="mt-6 space-y-2">
          <h3 className="text-sm font-medium text-slate-400 uppercase tracking-wider">
            Results
          </h3>
          {uploads.map((u, i) => (
            <div
              key={i}
              className="flex items-center gap-3 bg-slate-800 rounded-lg p-3 border border-slate-700"
            >
              {u.status === "success" && <CheckCircle className="w-5 h-5 text-emerald-400" />}
              {u.status === "error" && <AlertCircle className="w-5 h-5 text-red-400" />}
              {u.status === "duplicate" && <FileText className="w-5 h-5 text-amber-400" />}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{u.file}</p>
                <p className="text-xs text-slate-400">
                  {u.status === "success" &&
                    `${u.chunks} chunks · ${u.nodes} nodes · ${u.edges} edges`}
                  {u.status === "duplicate" && "Already ingested"}
                  {u.status === "error" && u.error}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}