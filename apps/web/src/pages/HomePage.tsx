import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Plus, FolderSearch, Globe, Lock } from "lucide-react";
import { api, ProjectSummary } from "../lib/api";
import { useAuth } from "../lib/authContext";
import UserMenu from "../components/UserMenu";
import NewCaseModal from "../components/NewCaseModal";
import { cn } from "../lib/utils";

interface HomePageProps {
  onOpenProject: (id: string) => void;
}

function CaseCard({ project, onOpen }: { project: ProjectSummary; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="text-left rounded-lg border border-[var(--hairline)] bg-[var(--panel)] hover:border-[var(--hairline-strong)] hover:bg-[var(--panel-raised)] transition-colors p-4 group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-8 h-8 rounded-md bg-[var(--panel-raised)] border border-[var(--hairline)] flex items-center justify-center rotate-[-2deg] group-hover:rotate-0 transition-transform">
          <FolderSearch className="w-4 h-4 text-[var(--thread)]" />
        </div>
        <span style={{ color: project.is_public ? "var(--verdict)" : "var(--wire)" }}>
          {project.is_public ? <Globe className="w-4 h-4" /> : <Lock className="w-4 h-4" />}
        </span>
      </div>
      <h3 className="text-[14px] font-medium text-[var(--ink)] leading-tight mb-1">{project.name}</h3>
      <p className="eyebrow">{new Date(project.created_at).toLocaleDateString()}</p>
    </button>
  );
}

export default function HomePage({ onOpenProject }: HomePageProps) {
  const { user } = useAuth();
  const [newCaseOpen, setNewCaseOpen] = useState(false);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects", user?.id ?? "anon"],
    queryFn: api.projects.list,
  });

  const mine = projects?.filter((p) => p.is_mine) ?? [];
  const publicCases = projects?.filter((p) => !p.is_mine) ?? [];

  return (
    <div className="min-h-screen bg-[var(--void)]">
      <header className="h-14 flex items-center justify-between px-4 border-b border-[var(--hairline)]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-[3px] bg-[var(--thread)] flex items-center justify-center rotate-[-3deg]">
            <span className="mono text-[11px] font-bold text-[var(--void)]">GS</span>
          </div>
          <span className="mono text-[13px] font-semibold tracking-tight text-[var(--ink)]">GraphSleuth</span>
        </div>
        <UserMenu onSignInClick={() => { window.location.hash = "#/login"; }} />
      </header>

      <main className="max-w-4xl mx-auto px-6 py-10">
        <div className="mb-8">
          <p className="eyebrow mb-1.5">Case archive</p>
          <h1 className="text-[22px] font-semibold text-[var(--ink)]">
            {user ? "Pick up a case, or open a new one" : "Explore public cases"}
          </h1>
          {!user && (
            <p className="text-[13px] text-[var(--ink-dim)] mt-1.5 max-w-[52ch]">
              Browse and ask questions about any public case below. Sign in to open your own private case.
            </p>
          )}
        </div>

        {user && (
          <section className="mb-9">
            <div className="flex items-center justify-between mb-3">
              <p className="eyebrow">My cases</p>
              <button
                onClick={() => setNewCaseOpen(true)}
                className="flex items-center gap-1.5 pl-2 pr-2.5 py-1 rounded-md bg-[var(--thread)] text-[var(--void)] text-[12px] font-medium hover:brightness-110 transition-all"
              >
                <Plus className="w-4 h-4" strokeWidth={2.5} />
                New case
              </button>
            </div>

            {isLoading && <p className="text-[13px] text-[var(--ink-faint)]">Loading…</p>}
            {!isLoading && mine.length === 0 && (
              <button
                onClick={() => setNewCaseOpen(true)}
                className="w-full rounded-lg border-2 border-dashed border-[var(--hairline)] hover:border-[var(--hairline-strong)] py-8 flex flex-col items-center justify-center transition-colors"
              >
                <Plus className="w-5 h-5 text-[var(--ink-faint)] mb-1.5" />
                <span className="text-[13px] text-[var(--ink-dim)]">Open your first case</span>
              </button>
            )}
            {mine.length > 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
                {mine.map((p) => (
                  <CaseCard key={p.id} project={p} onOpen={() => onOpenProject(p.id)} />
                ))}
              </div>
            )}
          </section>
        )}

        <section>
          <p className="eyebrow mb-3">Public cases</p>
          {!isLoading && publicCases.length === 0 && (
            <p className="text-[13px] text-[var(--ink-faint)]">No public cases yet.</p>
          )}
          <div className={cn("grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3")}>
            {publicCases.map((p) => (
              <CaseCard key={p.id} project={p} onOpen={() => onOpenProject(p.id)} />
            ))}
          </div>
        </section>
      </main>

      <NewCaseModal open={newCaseOpen} onClose={() => setNewCaseOpen(false)} onCreated={onOpenProject} />
    </div>
  );
}
