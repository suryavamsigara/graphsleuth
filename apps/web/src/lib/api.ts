const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
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

export const api = {
  health: () => fetchJson("/health/"),

  documents: {
    list: () => fetchJson("/documents/"),
    upload: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return fetch(`${API_BASE}/documents/upload`, {
        method: "POST",
        body: form,
      }).then((r) => r.json());
    },
  },

  query: {
    streamFetch: async (
      question: string,
      onEvent: (e: any) => void,
      opts: { top_k?: number; max_depth?: number; confidence_threshold?: number } = {},
      signal?: AbortSignal
    ) => {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

    sync: (question: string, top_k = 3, max_depth = 2, confidence_threshold = 0.35) =>
      fetchJson("/query/", {
        method: "POST",
        body: JSON.stringify({ question, top_k, max_depth, confidence_threshold }),
      }),
  },

  graph: {
    metrics: () => fetchJson("/graph/metrics"),
    searchNodes: (q: string, k = 5) =>
      fetchJson(`/graph/nodes/search?q=${encodeURIComponent(q)}&k=${k}`),
    getNode: (id: string) => fetchJson(`/graph/nodes/${id}`),
    getNodeEdges: (id: string) => fetchJson(`/graph/nodes/${id}/edges`),
    getChunk: (id: string) => fetchJson(`/graph/chunks/${id}`),
    traverse: (start_node_id: string, max_depth = 2, direction = "both") =>
      fetchJson("/graph/traverse", {
        method: "POST",
        body: JSON.stringify({ start_node_id, max_depth, direction }),
      }),
    evidenceGraph: (evidenceId: string) => fetchJson(`/graph/evidence/${evidenceId}`),
  },

  /**
   * the current backend (KnowledgeGraph / AsyncEngine) is wired as a
   * single lru_cache-d singleton per process. will workspace_id.
   */
  workspaces: {
    list: async (): Promise<{ id: string; name: string }[]> => {
      try {
        return await fetchJson("/workspaces/");
      } catch {
        return [{ id: "default", name: "Untitled Case" }];
      }
    },
  },
};
