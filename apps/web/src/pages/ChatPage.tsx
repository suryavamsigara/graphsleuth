import { useState, useRef, useCallback } from "react";
import { Send, Loader2, Bot, User, ChevronRight } from "lucide-react";
import { api } from "../lib/api";
import { cn } from "../lib/utils";
import { Link } from "react-router-dom";

interface Message {
  role: "user" | "assistant";
  content: string;
  evidenceId?: string;
  steps?: any[];
  latencyMs?: number;
  streaming?: boolean;
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!input.trim() || isLoading) return;

      const question = input.trim();
      setInput("");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: question },
        { role: "assistant", content: "", streaming: true },
      ]);
      setIsLoading(true);

      let answer = "";
      let evidenceId: string | undefined;
      let steps: any[] = [];
      let latencyMs = 0;

      try {
        await api.query.streamFetch(question, (event) => {
          if (event.type === "token") {
            answer += event.token;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                { ...last, content: answer, streaming: true },
              ];
            });
          } else if (event.type === "done") {
            evidenceId = event.evidence_id;
            steps = event.steps;
            latencyMs = event.latency_ms;
          } else if (event.type === "step") {
            // Could show step progress in UI
          }
        });
      } catch (err) {
        answer = `Error: ${err instanceof Error ? err.message : "Unknown error"}`;
      } finally {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last.role !== "assistant") return prev;
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              content: answer || "No answer generated.",
              streaming: false,
              evidenceId,
              steps,
              latencyMs,
            },
          ];
        });
        setIsLoading(false);
      }
    },
    [input, isLoading]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Bot className="w-12 h-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">Ask anything about your documents</p>
            <p className="text-sm">The agent will traverse the knowledge graph and cite sources.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-4 max-w-4xl",
              msg.role === "user" ? "ml-auto flex-row-reverse" : ""
            )}
          >
            <div
              className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                msg.role === "user" ? "bg-emerald-600" : "bg-slate-700"
              )}
            >
              {msg.role === "user" ? (
                <User className="w-4 h-4" />
              ) : (
                <Bot className="w-4 h-4" />
              )}
            </div>
            <div
              className={cn(
                "rounded-lg px-4 py-3 max-w-3xl",
                msg.role === "user"
                  ? "bg-emerald-900/30 border border-emerald-800"
                  : "bg-slate-800 border border-slate-700"
              )}
            >
              <div className="prose prose-invert prose-sm max-w-none">
                {msg.content}
                {msg.streaming && (
                  <span className="inline-block w-2 h-4 bg-emerald-400 animate-pulse ml-1" />
                )}
              </div>
              {msg.evidenceId && !msg.streaming && (
                <div className="mt-3 pt-3 border-t border-slate-700 flex items-center gap-2 text-xs">
                  <span className="text-slate-400">
                    {msg.steps?.length} reasoning steps · {msg.latencyMs}ms
                  </span>
                  <Link
                    to={`/evidence/${msg.evidenceId}`}
                    className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300"
                  >
                    View evidence <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-slate-800 p-4 bg-slate-900"
      >
        <div className="max-w-4xl mx-auto flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg px-4 py-3"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  );
}