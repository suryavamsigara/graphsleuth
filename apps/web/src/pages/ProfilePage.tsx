import { ArrowLeft, LogOut } from "lucide-react";
import { useAuth } from "../lib/authContext";

interface ProfilePageProps {
  onGoHome: () => void;
}

export default function ProfilePage({ onGoHome }: ProfilePageProps) {
  const { user, signOut } = useAuth();

  if (!user) {
    window.location.hash = "#/login";
    return null;
  }

  const displayName =
    (user.user_metadata?.name as string) ||
    user.email?.split("@")[0] ||
    "User";

  const initials = displayName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);

  return (
    <div className="min-h-screen bg-[var(--void)]">
      <header className="h-14 flex items-center justify-between px-4 border-b border-[var(--hairline)]">
        <button
          onClick={onGoHome}
          className="flex items-center gap-2"
        >
          <div className="w-6 h-6 rounded-[3px] bg-[var(--thread)] flex items-center justify-center rotate-[-3deg]">
            <span className="mono text-[11px] font-bold text-[var(--void)]">GS</span>
          </div>
          <span className="mono text-[13px] font-semibold tracking-tight text-[var(--ink)]">
            GraphSleuth
          </span>
        </button>
      </header>

      <main className="max-w-md mx-auto px-6 py-12">
        <button
          onClick={onGoHome}
          className="flex items-center gap-1.5 text-[12px] text-[var(--ink-faint)] hover:text-[var(--ink-dim)] transition-colors mb-8"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back to cases
        </button>

        <div className="rounded-lg border border-[var(--hairline)] bg-[var(--panel)] overflow-hidden">
          <div className="px-6 pt-8 pb-6 text-center border-b border-[var(--hairline)]">
            <div className="w-16 h-16 mx-auto rounded-full bg-[var(--thread)]/10 border-2 border-[var(--thread)] flex items-center justify-center mb-4">
              <span className="text-[20px] font-semibold text-[var(--thread)]">
                {initials}
              </span>
            </div>
            <h1 className="text-[16px] font-semibold text-[var(--ink)] mb-1">
              {displayName}
            </h1>
            <p className="text-[13px] text-[var(--ink-dim)]">{user.email}</p>
          </div>

          <div className="px-6 py-5 space-y-4">
            <div className="space-y-1">
              <p className="eyebrow">User ID</p>
              <p className="mono text-[12px] text-[var(--ink-dim)] break-all">
                {user.id}
              </p>
            </div>

            <button
              onClick={() => signOut().then(onGoHome)}
              className="w-full py-2.5 rounded-md border border-[var(--pin)]/30 text-[var(--pin)] text-[13px] font-medium hover:bg-[var(--pin)]/10 transition-colors flex items-center justify-center gap-2"
            >
              <LogOut className="w-3.5 h-3.5" />
              Sign out
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}