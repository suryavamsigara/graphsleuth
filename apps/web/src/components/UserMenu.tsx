import { LogIn, LogOut } from "lucide-react";
import { useAuth } from "../lib/authContext";

interface UserMenuProps {
  onSignInClick: () => void;
}

export default function UserMenu({ onSignInClick }: UserMenuProps) {
  const { user, signOut } = useAuth();

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
