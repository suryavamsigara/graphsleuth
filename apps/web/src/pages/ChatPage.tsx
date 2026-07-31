import { useState, useRef, useCallback, useEffect } from "react";
import { Send, Bot, User, ChevronRight, Sparkles } from "lucide-react";
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

function StreamingCursor() {
  return (
    <span className="inline-block w-[2px] h-4 bg-[var(--accent)] ml-0.5 animate-pulse align-middle" />
  );
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
              if (last?.role !== "assistant") return prev;
              return [...prev.slice(0, -1), { ...last, content: answer, streaming: true }];
            });
          } else if (event.type === "done") {
            evidenceId = event.evidence_id;
            steps = event.steps;
            latencyMs = event.latency_ms;
          }
        });
      } catch (err) {
        answer = `Error: ${err instanceof Error ? err.message : "Unknown error"}`;
      } finally {
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          if (last?.role !== "assistant") return prev;
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
    <div className="flex flex-col h-full max-w-3xl mx-auto">
      <div className="flex-1 overflow-auto px-6 py-8 space-y-6">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 animate-fade-in">
            <div className="w-12 h-12 rounded-2xl bg-[var(--accent)]/5 border border-[var(--accent)]/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-[var(--accent)]" />
            </div>
            <div>
              <p className="text-[15px] font-medium text-[var(--text-primary)]">
                Ask your knowledge graph
              </p>
              <p className="text-[13px] text-[var(--text-tertiary)] mt-1 max-w-xs mx-auto leading-relaxed">
                The agent traverses entities, reads source evidence, and synthesizes cited answers.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-3 animate-fade-in",
              msg.role === "user" && "flex-row-reverse"
            )}
          >
            <div
              className={cn(
                "w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-1",
                msg.role === "user"
                  ? "bg-[var(--accent)]/10"
                  : "bg-[var(--bg-raised)] border border-[var(--border-subtle)]"
              )}
            >
              {msg.role === "user" ? (
                <User className="w-3 h-3 text-[var(--accent)]" />
              ) : (
                <Bot className="w-3 h-3 text-[var(--text-tertiary)]" />
              )}
            </div>

            <div
              className={cn(
                "max-w-[85%] rounded-2xl px-4 py-3",
                msg.role === "user"
                  ? "bg-[var(--accent)]/10 text-[var(--text-primary)] rounded-tr-sm"
                  : "bg-transparent text-[var(--text-secondary)] rounded-tl-sm"
              )}
            >
              <div className="prose-custom">
                {msg.content}
                {msg.streaming && <StreamingCursor />}
              </div>

              {msg.evidenceId && !msg.streaming && (
                <div className="mt-3 pt-3 border-t border-[var(--border-subtle)] flex items-center justify-between">
                  <span className="text-[11px] text-[var(--text-muted)] tabular-nums">
                    {msg.latencyMs}ms · {msg.steps?.length || 0} steps
                  </span>
                  <Link
                    to={`/evidence/${msg.evidenceId}`}
                    className="flex items-center gap-1 text-[11px] font-medium text-[var(--accent)] hover:text-[var(--accent-dim)] transition-colors"
                  >
                    Evidence <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[var(--border-subtle)] p-4 bg-[var(--bg-base)]">
        <form onSubmit={handleSubmit} className="relative">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            className="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-xl pl-4 pr-12 py-3 text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)]/30 focus:ring-1 focus:ring-[var(--accent)]/20 transition-all"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 disabled:opacity-30 disabled:hover:bg-[var(--accent)]/10 transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}