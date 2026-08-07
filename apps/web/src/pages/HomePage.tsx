import { useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Plus,
  FolderSearch,
  Globe,
  Lock,
  Search,
  ArrowDown,
  Workflow,
  ChevronRight,
} from "lucide-react";
import { motion } from "framer-motion";
import { api, ProjectSummary } from "../lib/api";
import { useAuth } from "../lib/authContext";
import UserMenu from "../components/UserMenu";
import NewCaseModal from "../components/NewCaseModal";
import { cn } from "../lib/utils";

interface HomePageProps {
  onOpenProject: (id: string) => void;
}

function CaseCard({
  project,
  onOpen,
  index,
}: {
  project: ProjectSummary;
  onOpen: () => void;
  index: number;
}) {
  return (
    <motion.button
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.05, ease: [0.16, 1, 0.3, 1] }}
      onClick={onOpen}
      className="group text-left rounded-xl border border-[var(--hairline)] bg-[var(--panel)] hover:border-[var(--thread)]/40 hover:bg-[var(--panel-raised)] transition-all duration-300 p-5 relative overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-[var(--thread)]/0 to-[var(--thread)]/0 group-hover:from-[var(--thread)]/[0.03] group-hover:to-transparent transition-all duration-500" />

      <div className="relative">
        <div className="flex items-start justify-between mb-4">
          <div className="w-10 h-10 rounded-lg bg-[var(--panel-raised)] border border-[var(--hairline)] flex items-center justify-center group-hover:scale-105 group-hover:rotate-[-1deg] transition-transform duration-300">
            <FolderSearch className="w-5 h-5 text-[var(--thread)]" />
          </div>
          <span
            className={cn(
              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border",
              project.is_public
                ? "bg-[var(--verdict)]/10 text-[var(--verdict)] border-[var(--verdict)]/20"
                : "bg-[var(--ink-faint)]/10 text-[var(--ink-faint)] border-[var(--hairline)]"
            )}
          >
            {project.is_public ? (
              <Globe className="w-3 h-3" />
            ) : (
              <Lock className="w-3 h-3" />
            )}
            {project.is_public ? "Public" : "Private"}
          </span>
        </div>

        <h3 className="text-[15px] font-semibold text-[var(--ink)] leading-snug mb-1.5 group-hover:text-[var(--thread)] transition-colors duration-300">
          {project.name}
        </h3>

        <p className="text-[12px] text-[var(--ink-dim)] mb-4">
          Created{" "}
          {new Date(project.created_at).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </p>

        <div className="flex items-center text-[11px] text-[var(--ink-faint)] group-hover:text-[var(--thread)] transition-colors duration-300">
          <span>Open project</span>
          <ChevronRight className="w-3 h-3 ml-0.5 group-hover:translate-x-0.5 transition-transform duration-300" />
        </div>
      </div>
    </motion.button>
  );
}

export default function HomePage({ onOpenProject }: HomePageProps) {
  const { user } = useAuth();
  const [newCaseOpen, setNewCaseOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const publicSectionRef = useRef<HTMLDivElement>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["projects", user?.id ?? "anon"],
    queryFn: api.projects.list,
  });

  const mine = projects?.filter((p) => p.is_mine) ?? [];
  const publicCases = projects?.filter((p) => !p.is_mine) ?? [];

  const filteredMine = mine.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const filteredPublic = publicCases.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const scrollToPublic = () => {
    publicSectionRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  return (
    <div className="min-h-screen bg-[var(--void)] text-[var(--ink)]">
      {/* Sticky Header */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-[var(--hairline)] bg-[var(--void)]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-[4px] bg-[var(--thread)] flex items-center justify-center rotate-[-3deg]">
            <Workflow className="w-3.5 h-3.5 text-[var(--void)]" />
          </div>
          <span className="mono text-[14px] font-semibold tracking-tight">
            GraphSleuth
          </span>
        </div>
        <UserMenu
          onSignInClick={() => {
            window.location.hash = "#/login";
          }}
        />
      </header>

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-6 overflow-hidden">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[300px] bg-[var(--thread)]/[0.07] rounded-full blur-[100px]" />
        </div>

        <div className="relative max-w-3xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--thread)]/10 border border-[var(--thread)]/20 text-[var(--thread)] text-[11px] font-medium mb-6">
              <Workflow className="w-3 h-3" />
              Knowledge Graph RAG
            </span>

            <h1 className="text-[40px] sm:text-[52px] font-bold tracking-tight leading-[1.1] mb-6 text-[var(--ink)]">
              Turn documents into
              <br />
              <span className="text-[var(--thread)]">
                living knowledge graphs
              </span>
            </h1>

            <p className="text-[16px] sm:text-[17px] text-[var(--ink-dim)] leading-relaxed max-w-xl mx-auto mb-10">
              Extract entities, map relationships, and reason across your
              documents with full traceability. Every answer includes source references.
            </p>

            {/* Search Bar */}
            <div className="max-w-md mx-auto mb-8">
              <div className="relative group">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--ink-faint)] group-focus-within:text-[var(--thread)] transition-colors" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search projects by name..."
                  className="w-full bg-[var(--panel)] border border-[var(--hairline)] rounded-xl pl-11 pr-4 py-3.5 text-[14px] text-[var(--ink)] placeholder:text-[var(--ink-faint)] focus:outline-none focus:border-[var(--thread)]/50 focus:ring-1 focus:ring-[var(--thread)]/20 transition-all"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery("")}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] uppercase tracking-wider text-[var(--ink-faint)] hover:text-[var(--ink)] transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>

            {/* CTAs */}
            <div className="flex items-center justify-center gap-3 flex-wrap">
              {user && (
                <button
                  onClick={() => setNewCaseOpen(true)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[var(--thread)] text-[var(--void)] text-[13px] font-semibold hover:brightness-110 active:scale-[0.98] transition-all"
                >
                  <Plus className="w-4 h-4" strokeWidth={2.5} />
                  New project
                </button>
              )}
              <button
                onClick={scrollToPublic}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-[var(--hairline)] bg-[var(--panel)] text-[var(--ink-dim)] text-[13px] font-medium hover:border-[var(--hairline-strong)] hover:text-[var(--ink)] transition-all"
              >
                <Globe className="w-4 h-4" />
                Browse public projects
                <ArrowDown className="w-3 h-3" />
              </button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-6 pb-24">
        {/* My Cases */}
        {user && (
          <section className="mb-16">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-[20px] font-semibold text-[var(--ink)] mb-1">
                  My projects
                </h2>
                <p className="text-[13px] text-[var(--ink-dim)]">
                  {filteredMine.length}{" "}
                  {filteredMine.length === 1 ? "project" : "projects"}
                  {searchQuery && " matching your search"}
                </p>
              </div>
              <button
                onClick={() => setNewCaseOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--panel)] border border-[var(--hairline)] text-[12px] font-medium text-[var(--ink-dim)] hover:text-[var(--ink)] hover:border-[var(--hairline-strong)] transition-all"
              >
                <Plus className="w-3.5 h-3.5" />
                New project
              </button>
            </div>

            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {[...Array(3)].map((_, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-[var(--hairline)] bg-[var(--panel)] p-5 h-40 animate-pulse"
                  />
                ))}
              </div>
            ) : filteredMine.length === 0 ? (
              <div className="rounded-xl border border-dashed border-[var(--hairline)] bg-[var(--panel)]/50 p-12 text-center">
                <div className="w-12 h-12 rounded-full bg-[var(--panel-raised)] border border-[var(--hairline)] flex items-center justify-center mx-auto mb-4">
                  <FolderSearch className="w-5 h-5 text-[var(--ink-faint)]" />
                </div>
                <h3 className="text-[15px] font-medium text-[var(--ink)] mb-1">
                  {searchQuery ? "No projects match your search" : "No projects yet"}
                </h3>
                <p className="text-[13px] text-[var(--ink-dim)] mb-4 max-w-sm mx-auto">
                  {searchQuery
                    ? "Try adjusting your search terms"
                    : "Create your first project to start investigating documents"}
                </p>
                {!searchQuery && (
                  <button
                    onClick={() => setNewCaseOpen(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--thread)] text-[var(--void)] text-[12px] font-medium hover:brightness-110 transition-all"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Create a project
                  </button>
                )}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredMine.map((p, i) => (
                  <CaseCard
                    key={p.id}
                    project={p}
                    onOpen={() => onOpenProject(p.id)}
                    index={i}
                  />
                ))}
              </div>
            )}
          </section>
        )}

        {/* Public Cases */}
        <section ref={publicSectionRef}>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-[20px] font-semibold text-[var(--ink)] mb-1">
                Public projects
              </h2>
              <p className="text-[13px] text-[var(--ink-dim)]">
                {filteredPublic.length}{" "}
                {filteredPublic.length === 1 ? "project" : "projects"} available to
                explore
                {searchQuery && " matching your search"}
              </p>
            </div>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div
                  key={i}
                  className="rounded-xl border border-[var(--hairline)] bg-[var(--panel)] p-5 h-40 animate-pulse"
                />
              ))}
            </div>
          ) : filteredPublic.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[var(--hairline)] bg-[var(--panel)]/50 p-12 text-center">
              <div className="w-12 h-12 rounded-full bg-[var(--panel-raised)] border border-[var(--hairline)] flex items-center justify-center mx-auto mb-4">
                <Globe className="w-5 h-5 text-[var(--ink-faint)]" />
              </div>
              <h3 className="text-[15px] font-medium text-[var(--ink)] mb-1">
                {searchQuery
                  ? "No public projects match your search"
                  : "No public projects yet"}
              </h3>
              <p className="text-[13px] text-[var(--ink-dim)] max-w-sm mx-auto">
                {searchQuery
                  ? "Try adjusting your search terms"
                  : "Public projects will appear here when the community shares them"}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredPublic.map((p, i) => (
                <CaseCard
                  key={p.id}
                  project={p}
                  onOpen={() => onOpenProject(p.id)}
                  index={i}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <NewCaseModal
        open={newCaseOpen}
        onClose={() => setNewCaseOpen(false)}
        onCreated={onOpenProject}
      />
    </div>
  );
}