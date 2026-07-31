import { Link, useLocation } from "react-router-dom";
import { MessageSquare, Upload, Network, FlaskConical } from "lucide-react";
import { cn } from "../lib/utils";

const nav = [
  { path: "/", label: "Chat", icon: MessageSquare },
  { path: "/ingest", label: "Ingest", icon: Upload },
  { path: "/explore", label: "Explore", icon: Network },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation();

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <aside className="w-64 border-r border-slate-800 bg-slate-900 flex flex-col">
        <div className="p-4 border-b border-slate-800 flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-emerald-400" />
          <h1 className="font-bold text-lg tracking-tight">GraphSleuth</h1>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {nav.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                location.pathname === item.path
                  ? "bg-slate-800 text-emerald-400"
                  : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800 text-xs text-slate-500">
          v0.1.0 — Graph RAG
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}