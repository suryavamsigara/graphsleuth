import { useState } from "react";
import { FolderSearch, Mail, Lock, User as UserIcon, Loader2, ArrowLeft, Check } from "lucide-react";
import { useAuth } from "../lib/authContext";
import { cn } from "../lib/utils";

interface AuthPageProps {
  mode: "login" | "register";
  onSwitchMode: (mode: "login" | "register") => void;
  onDone: () => void; // navigate back to where they came from
}

export default function AuthPage({ mode, onSwitchMode, onDone }: AuthPageProps) {
  const { signInWithPassword, signUpWithPassword, signInWithEmail } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmSent, setConfirmSent] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const isRegister = mode === "register";

  const submit = async () => {
    setError(null);
    if (!email.trim() || !password.trim() || (isRegister && !name.trim())) {
      setError("Fill in all fields.");
      return;
    }
    setBusy(true);
    try {
      if (isRegister) {
        const { error } = await signUpWithPassword(email.trim(), password, name.trim());
        if (error) {
          setError(error);
        } else {
          // Supabase returns no active session until the confirmation link
          // is clicked, if email confirmation is enabled on the project.
          setConfirmSent(true);
        }
      } else {
        const { error } = await signInWithPassword(email.trim(), password);
        if (error) {
          setError(error);
        } else {
          onDone();
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const sendMagicLink = async () => {
    if (!email.trim()) {
      setError("Enter your email first.");
      return;
    }
    setBusy(true);
    setError(null);
    const { error } = await signInWithEmail(email.trim());
    setBusy(false);
    if (error) setError(error);
    else setMagicLinkSent(true);
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "var(--void)", backgroundImage: "var(--board-dot)", backgroundSize: "18px 18px" }}
    >
      <div className="w-full max-w-sm">
        <button
          onClick={onDone}
          className="flex items-center gap-1.5 text-[12px] text-[var(--ink-faint)] hover:text-[var(--ink-dim)] transition-colors mb-6"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to projects
        </button>

        <div className="rounded-lg border border-[var(--hairline)] bg-[var(--panel)] overflow-hidden">
          <div className="px-6 pt-6 pb-5 border-b border-[var(--hairline)] text-center">
            <div className="w-9 h-9 mx-auto rounded-md bg-[var(--thread)] flex items-center justify-center rotate-[-3deg] mb-3">
              <FolderSearch className="w-4.5 h-4.5 text-[var(--void)]" />
            </div>
            <p className="eyebrow mb-1">{isRegister ? "New investigator" : "Welcome back"}</p>
            <h1 className="text-[16px] font-semibold text-[var(--ink)]">
              {isRegister ? "Create your account" : "Sign in"}
            </h1>
          </div>

          <div className="px-6 py-5 space-y-3">
            {confirmSent ? (
              <div className="flex items-start gap-2 text-[13px] text-[var(--verdict)] py-2">
                <Check className="w-4 h-4 mt-0.5 shrink-0" />
                <span>Account created — check your email to confirm it, then sign in.</span>
              </div>
            ) : magicLinkSent ? (
              <div className="flex items-start gap-2 text-[13px] text-[var(--verdict)] py-2">
                <Check className="w-4 h-4 mt-0.5 shrink-0" />
                <span>Check your inbox for a sign-in link.</span>
              </div>
            ) : (
              <>
                {isRegister && (
                  <Field icon={UserIcon} value={name} onChange={setName} placeholder="Full name" type="text" />
                )}
                <Field icon={Mail} value={email} onChange={setEmail} placeholder="you@example.com" type="email" />
                <Field
                  icon={Lock}
                  value={password}
                  onChange={setPassword}
                  placeholder="Password"
                  type="password"
                  onEnter={submit}
                />

                {error && <p className="text-[12px] text-[var(--pin)]">{error}</p>}

                <button
                  onClick={submit}
                  disabled={busy}
                  className={cn(
                    "w-full py-2 rounded-md text-[13px] font-medium transition-all flex items-center justify-center gap-1.5",
                    busy ? "bg-[var(--hairline)] text-[var(--ink-faint)]" : "bg-[var(--thread)] text-[var(--void)] hover:brightness-110"
                  )}
                >
                  {busy && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  {isRegister ? "Create account" : "Sign in"}
                </button>

                <div className="flex items-center gap-2 py-1">
                  <div className="flex-1 h-px bg-[var(--hairline)]" />
                  <span className="eyebrow">or</span>
                  <div className="flex-1 h-px bg-[var(--hairline)]" />
                </div>

                <button
                  onClick={sendMagicLink}
                  disabled={busy}
                  className="w-full py-2 rounded-md text-[13px] text-[var(--ink-dim)] border border-[var(--hairline)] hover:border-[var(--hairline-strong)] hover:text-[var(--ink)] transition-colors"
                >
                  Email me a sign-in link instead
                </button>
              </>
            )}
          </div>

          <div className="px-6 py-3.5 border-t border-[var(--hairline)] text-center">
            <button
              onClick={() => {
                setError(null);
                setConfirmSent(false);
                setMagicLinkSent(false);
                onSwitchMode(isRegister ? "login" : "register");
              }}
              className="text-[12px] text-[var(--ink-dim)] hover:text-[var(--ink)]"
            >
              {isRegister ? (
                <>Already have a project file? <span className="text-[var(--thread)]">Sign in</span></>
              ) : (
                <>New here? <span className="text-[var(--thread)]">Create an account</span></>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  icon: Icon,
  value,
  onChange,
  placeholder,
  type,
  onEnter,
}: {
  icon: typeof Mail;
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  type: string;
  onEnter?: () => void;
}) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-[var(--hairline)] bg-[var(--panel-raised)] px-3 py-2 focus-within:border-[var(--thread)] transition-colors">
      <Icon className="w-3.5 h-3.5 text-[var(--ink-faint)] shrink-0" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onEnter?.()}
        type={type}
        placeholder={placeholder}
        className="flex-1 bg-transparent text-[13px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none min-w-0"
      />
    </div>
  );
}
