import { supabase } from "./supabaseClient";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchJson(path: string, options: RequestInit = {}, projectId?: string) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(await authHeaders()),
    ...(projectId ? { "X-Project-Id": projectId } : {}),
    ...(options.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export interface ReasoningStep {
  step: number;
  action: string;
  input: unknown;
  output: unknown;
  latency_ms: number;
}

export interface QueryDoneEvent {
  type: "done";
  answer: string;
  evidence_id: string;
  tokens_used: number;
  latency_ms: number;
  confidence: number; // 0-1
  steps: ReasoningStep[];
}

export interface ProjectSummary {
  id: string;
  name: string;
  owner_id: string;
  is_public: boolean;
  created_at: string;
  is_mine: boolean;
}

export const api = {
  health: () => fetchJson("/health/"),

  projects: {
    list: (): Promise<ProjectSummary[]> => fetchJson("/projects/"),
    listPublic: (): Promise<ProjectSummary[]> => fetchJson("/projects/public"),
    get: (projectId: string): Promise<ProjectSummary> => fetchJson(`/projects/${projectId}`),
    create: (name: string, isPublic: boolean): Promise<ProjectSummary> =>
      fetchJson("/projects/", { method: "POST", body: JSON.stringify({ name, is_public: isPublic }) }),
    update: (projectId: string, patch: { name?: string; is_public?: boolean }): Promise<ProjectSummary> =>
      fetchJson(`/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(patch) }),
    remove: (projectId: string) => fetchJson(`/projects/${projectId}`, { method: "DELETE" }),
  },

  documents: {
    list: (projectId: string) => fetchJson("/documents/", {}, projectId),
    upload: async (projectId: string, file: File) => {
      const form = new FormData();
      form.append("file", file);
      const headers = { ...(await authHeaders()), "X-Project-Id": projectId };
      const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form, headers });
      if (!res.ok) throw new Error(await res.text());
      return res.json();
    },
  },

  query: {
    /**
     * Streams SSE events from POST /query/stream via fetch + ReadableStream.
     * (Native EventSource can't send a POST body or custom headers, which
     * is why this isn't built on EventSource.)
     */
    streamFetch: async (
      projectId: string,
      question: string,
      onEvent: (e: any) => void,
      opts: { top_k?: number; max_depth?: number; confidence_threshold?: number } = {},
      signal?: AbortSignal
    ) => {
      const headers = {
        "Content-Type": "application/json",
        ...(await authHeaders()),
        "X-Project-Id": projectId,
      };
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question,
          top_k: opts.top_k ?? 3,
          max_depth: opts.max_depth ?? 2,
          confidence_threshold: opts.confidence_threshold ?? 0.35,
        }),
        signal,
      });

      if (!res.ok || !res.body) throw new Error(await res.text());

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const dataLine = line.split("\n").find((l) => l.startsWith("data: "));
          if (!dataLine) continue;
          try {
            onEvent(JSON.parse(dataLine.slice(6)));
          } catch {
            // ignore malformed SSE frame
          }
        }
      }
    },

    sync: (projectId: string, question: string, top_k = 3, max_depth = 2, confidence_threshold = 0.35) =>
      fetchJson(
        "/query/",
        { method: "POST", body: JSON.stringify({ question, top_k, max_depth, confidence_threshold }) },
        projectId
      ),
  },

  graph: {
    metrics: (projectId: string) => fetchJson("/graph/metrics", {}, projectId),
    searchNodes: (projectId: string, q: string, k = 5) =>
      fetchJson(`/graph/nodes/search?q=${encodeURIComponent(q)}&k=${k}`, {}, projectId),
    getNode: (projectId: string, id: string) => fetchJson(`/graph/nodes/${id}`, {}, projectId),
    getNodeEdges: (projectId: string, id: string) => fetchJson(`/graph/nodes/${id}/edges`, {}, projectId),
    getChunk: (projectId: string, id: string) => fetchJson(`/graph/chunks/${id}`, {}, projectId),
    traverse: (projectId: string, start_node_id: string, max_depth = 2, direction = "both") =>
      fetchJson(
        "/graph/traverse",
        { method: "POST", body: JSON.stringify({ start_node_id, max_depth, direction }) },
        projectId
      ),
    evidenceGraph: (projectId: string, evidenceId: string) =>
      fetchJson(`/graph/evidence/${evidenceId}`, {}, projectId),
  },
};
