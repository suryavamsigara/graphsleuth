import { LogIn } from "lucide-react";
import { useAuth } from "../lib/authContext";

interface UserMenuProps {
  onSignInClick: () => void;
}

export default function UserMenu({ onSignInClick }: UserMenuProps) {
  const { user } = useAuth();

  if (user) {
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
      <button
        onClick={() => {
          window.location.hash = "#/profile";
        }}
        className="flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-[var(--hairline)] text-[12px] text-[var(--ink-dim)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-colors"
        title={user.email ?? undefined}
      >
        <div className="w-5 h-5 rounded-full bg-[var(--thread)]/10 border border-[var(--thread)]/30 flex items-center justify-center">
          <span className="text-[9px] font-semibold text-[var(--thread)]">
            {initials}
          </span>
        </div>
        <span className="mono truncate max-w-[10ch]">
          {user.email?.split("@")[0]}
        </span>
      </button>
    );
  }

  return (
    <button
      onClick={onSignInClick}
      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border border-[var(--hairline)] text-[12px] text-[var(--ink-dim)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-colors"
    >
      <LogIn className="w-3.5 h-3.5" />
      Sign in
    </button>
  );
}
