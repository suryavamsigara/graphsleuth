import { Link, useLocation } from "react-router-dom";
import { MessageSquare, Upload, Network, FlaskConical } from "lucide-react";
import { cn } from "../lib/utils";

const nav = [
  { path: "/", label: "Ask", icon: MessageSquare },
  { path: "/ingest", label: "Ingest", icon: Upload },
  { path: "/explore", label: "Explore", icon: Network },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-[var(--bg-void)] text-[var(--text-primary)] overflow-hidden">
      <aside className="w-56 flex-shrink-0 flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-base)]">
        <div className="px-5 py-6">
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-7 h-7 rounded-lg bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center">
              <FlaskConical className="w-3.5 h-3.5 text-[var(--accent)]" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight leading-none group-hover:text-[var(--accent)] transition-colors">
                GraphSleuth
              </h1>
              <p className="text-[10px] text-[var(--text-muted)] mt-0.5 tracking-wide">
                Knowledge Graph RAG
              </p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-3 space-y-0.5">
          {nav.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all duration-200",
                  isActive
                    ? "bg-[var(--accent)]/10 text-[var(--accent)]"
                    : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)]"
                )}
              >
                <item.icon className={cn("w-4 h-4", isActive && "text-[var(--accent)]")} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="px-5 py-4 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
            <span className="text-[11px] text-[var(--text-muted)]">System Online</span>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-hidden relative">
        {children}
      </main>
    </div>
  );
}