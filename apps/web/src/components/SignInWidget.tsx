import { useState, useRef, useEffect } from "react";
import { LogIn, LogOut, Mail, Loader2, Check } from "lucide-react";
import { useAuth } from "../lib/authContext";
import { cn } from "../lib/utils";

export default function SignInWidget() {
  const { user, signInWithEmail, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  if (user) {
    return (
      <button
        onClick={() => signOut()}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-[var(--hairline)] text-[12px] text-[var(--ink-dim)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-colors"
        title={user.email ?? undefined}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--verdict)]" />
        <span className="mono truncate max-w-[10ch]">{user.email?.split("@")[0]}</span>
        <LogOut className="w-3 h-3 text-[var(--ink-faint)]" />
      </button>
    );
  }

  const send = async () => {
    if (!email.trim()) return;
    setStatus("sending");
    setError(null);
    const { error } = await signInWithEmail(email.trim());
    if (error) {
      setStatus("error");
      setError(error);
    } else {
      setStatus("sent");
    }
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-[var(--hairline)] text-[12px] text-[var(--ink-dim)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-colors"
      >
        <LogIn className="w-3.5 h-3.5" />
        Sign in
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-1.5 w-64 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] shadow-2xl z-40 p-3">
          {status === "sent" ? (
            <div className="flex items-start gap-2 text-[12px] text-[var(--verdict)]">
              <Check className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>Check your inbox for a sign-in link.</span>
            </div>
          ) : (
            <>
              <p className="eyebrow mb-2">Sign in with email</p>
              <div className="flex items-center gap-1.5 rounded-md border border-[var(--hairline)] bg-[var(--panel)] px-2 py-1.5 focus-within:border-[var(--thread)]">
                <Mail className="w-3.5 h-3.5 text-[var(--ink-faint)] shrink-0" />
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && send()}
                  type="email"
                  placeholder="you@example.com"
                  className="flex-1 bg-transparent text-[12px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none min-w-0"
                />
              </div>
              {error && <p className="text-[11px] text-[var(--pin)] mt-1.5">{error}</p>}
              <button
                onClick={send}
                disabled={status === "sending" || !email.trim()}
                className={cn(
                  "w-full mt-2 py-1.5 rounded-md text-[12px] font-medium transition-all flex items-center justify-center gap-1.5",
                  status === "sending" || !email.trim()
                    ? "bg-[var(--hairline)] text-[var(--ink-faint)]"
                    : "bg-[var(--thread)] text-[var(--void)] hover:brightness-110"
                )}
              >
                {status === "sending" ? <Loader2 className="w-3 h-3 animate-spin" /> : "Send magic link"}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
