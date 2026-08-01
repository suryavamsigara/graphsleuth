import { useCallback, useRef, useState } from "react";
import { ArrowUp, Loader2 } from "lucide-react";
import { api, ReasoningStep } from "../lib/api";
import ReasoningTrail from "./ReasoningTrail";
import { cn } from "../lib/utils";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  steps: ReasoningStep[];
  confidence?: number;
  latencyMs?: number;
  evidenceId?: string;
  streaming?: boolean;
  error?: string;
}

interface ChatPanelProps {
  projectId: string;
  onEvidence: (evidenceId: string) => void; // tells ExplorePage to render the resulting evidence graph
}

const DEPTH_OPTIONS = [
  { value: 1, label: "Shallow · 1 hop" },
  { value: 2, label: "Standard · 2 hops" },
  { value: 3, label: "Deep · 3 hops" },
  { value: 4, label: "Exhaustive · 4 hops" },
];

const CONFIDENCE_OPTIONS = [
  { value: 0.2, label: "Loose · 0.20" },
  { value: 0.35, label: "Balanced · 0.35" },
  { value: 0.5, label: "Strict · 0.50" },
  { value: 0.65, label: "Very strict · 0.65" },
];

export default function ChatPanel({ projectId, onEvidence }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [maxDepth, setMaxDepth] = useState(2);
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.35);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }, []);

  const send = useCallback(async () => {
    const question = input.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: "user", text: question, steps: [] };
    const assistantId = crypto.randomUUID();
    const assistantMsg: ChatMessage = { id: assistantId, role: "assistant", text: "", steps: [], streaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    scrollToBottom();

    try {
      await api.query.streamFetch(
        projectId,
        question,
        (event) => {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              if (event.type === "step") {
                return { ...m, steps: [...m.steps, event] };
              }
              if (event.type === "token") {
                return { ...m, text: m.text + event.token };
              }
              if (event.type === "evidence") {
                return { ...m, evidenceId: event.data?.id };
              }
              if (event.type === "done") {
                onEvidence(event.evidence_id);
                return {
                  ...m,
                  text: event.answer || m.text,
                  steps: event.steps ?? m.steps,
                  confidence: event.confidence,
                  latencyMs: event.latency_ms,
                  evidenceId: event.evidence_id,
                  streaming: false,
                };
              }
              if (event.type === "error") {
                return { ...m, error: event.message, streaming: false };
              }
              return m;
            })
          );
          scrollToBottom();
        },
        { max_depth: maxDepth, confidence_threshold: confidenceThreshold }
      );
    } catch (e: any) {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? { ...m, error: String(e.message || e), streaming: false } : m))
      );
    } finally {
      setBusy(false);
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, streaming: false } : m)));
    }
  }, [input, busy, maxDepth, confidenceThreshold, projectId, onEvidence, scrollToBottom]);

  return (
    <div className="flex flex-col h-full bg-[var(--panel)]">
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--hairline)] shrink-0">
        <span className="eyebrow mr-1">Interview settings</span>

        <select
          value={maxDepth}
          onChange={(e) => setMaxDepth(Number(e.target.value))}
          className="mono text-[11px] bg-[var(--panel-raised)] border border-[var(--hairline)] rounded px-2 py-1 text-[var(--ink-dim)] focus:outline-none focus:border-[var(--thread)] cursor-pointer"
        >
          {DEPTH_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>

        <select
          value={confidenceThreshold}
          onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
          className="mono text-[11px] bg-[var(--panel-raised)] border border-[var(--hairline)] rounded px-2 py-1 text-[var(--ink-dim)] focus:outline-none focus:border-[var(--thread)] cursor-pointer"
        >
          {CONFIDENCE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-6">
            <p className="eyebrow mb-2">Case open</p>
            <p className="text-[13px] text-[var(--ink-dim)] max-w-[26ch]">
              Ask a question about your documents. Every answer shows its work — entry points, hops, and sources.
            </p>
          </div>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <div key={m.id} className="flex justify-end">
              <div className="max-w-[85%] rounded-lg rounded-tr-sm bg-[var(--panel-raised)] border border-[var(--hairline)] px-3 py-2 text-[13px] text-[var(--ink)]">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={m.id} className="space-y-2">
              {m.steps.length > 0 && (
                <ReasoningTrail steps={m.steps} confidence={m.confidence} latencyMs={m.latencyMs} live={m.streaming} />
              )}
              {m.error ? (
                <p className="text-[13px] text-[var(--pin)]">{m.error}</p>
              ) : (
                <p className="text-[13px] text-[var(--ink)] leading-relaxed whitespace-pre-wrap">
                  {m.text}
                  {m.streaming && <span className="inline-block w-1.5 h-3.5 bg-[var(--thread)] ml-0.5 align-middle animate-pulse" />}
                </p>
              )}
            </div>
          )
        )}
      </div>

      <div className="p-3 border-t border-[var(--hairline)] shrink-0">
        <div className="flex items-end gap-2 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] focus-within:border-[var(--thread)] transition-colors px-3 py-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            placeholder="Ask about the case…"
            className="flex-1 bg-transparent resize-none text-[13px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none max-h-32"
          />
          <button
            onClick={send}
            disabled={busy || !input.trim()}
            className={cn(
              "w-7 h-7 rounded-md flex items-center justify-center shrink-0 transition-all",
              busy || !input.trim() ? "bg-[var(--hairline)] text-[var(--ink-faint)]" : "bg-[var(--thread)] text-[var(--void)] hover:brightness-110"
            )}
          >
            {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ArrowUp className="w-3.5 h-3.5" strokeWidth={2.5} />}
          </button>
        </div>
      </div>
    </div>
  );
}
