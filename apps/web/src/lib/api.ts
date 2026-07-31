const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function fetchJson(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
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
    stream: (question: string, onEvent: (e: any) => void, signal?: AbortSignal) => {
      return new Promise<void>((resolve, reject) => {
        const es = new EventSource(
          `${API_BASE}/query/stream`,
          { body: JSON.stringify({ question }), method: "POST" } as any
        );
        // Actually EventSource doesn't support POST. Use fetch + ReadableStream instead:
      });
    },

    // Better: use fetch with ReadableStream for POST-based SSE
    streamFetch: async (
      question: string,
      onEvent: (e: any) => void,
      top_k = 3,
      max_depth = 2
    ) => {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k, max_depth }),
      });

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch {
              // ignore malformed
            }
          }
        }
      }
    },

    sync: (question: string, top_k = 3, max_depth = 2) =>
      fetchJson("/query/", {
        method: "POST",
        body: JSON.stringify({ question, top_k, max_depth }),
      }),
  },

  graph: {
    metrics: () => fetchJson("/graph/metrics"),
    searchNodes: (q: string, k = 5) =>
      fetchJson(`/graph/nodes/search?q=${encodeURIComponent(q)}&k=${k}`),
    getNode: (id: string) => fetchJson(`/graph/nodes/${id}`),
    traverse: (start_node_id: string, max_depth = 2, direction = "both") =>
      fetchJson("/graph/traverse", {
        method: "POST",
        body: JSON.stringify({ start_node_id, max_depth, direction }),
      }),
    evidenceGraph: (evidenceId: string) =>
      fetchJson(`/graph/evidence/${evidenceId}`),
  },
};