import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./styles/tokens.css";
import { AuthProvider } from "./lib/authContext";
import HomePage from "./pages/HomePage";
import ExplorePage from "./pages/ExplorePage";
import AuthPage from "./pages/AuthPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
});

function useRoute() {
  const [hash, setHash] = useState(window.location.hash);

  useEffect(() => {
    const onChange = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const caseMatch = hash.match(/^#\/case\/(.+)$/);
  const isLogin = hash === "#/login";
  const isRegister = hash === "#/register";

  return {
    projectId: caseMatch ? decodeURIComponent(caseMatch[1]) : null,
    authMode: isLogin ? ("login" as const) : isRegister ? ("register" as const) : null,
  };
}

function Router() {
  const { projectId, authMode } = useRoute();

  const goHome = () => {
    window.location.hash = "";
  };
  const openCase = (id: string) => {
    window.location.hash = `#/case/${encodeURIComponent(id)}`;
  };

  if (authMode) {
    return (
      <AuthPage
        mode={authMode}
        onSwitchMode={(m) => { window.location.hash = m === "login" ? "#/login" : "#/register"; }}
        onDone={goHome}
      />
    );
  }

  if (projectId) {
    return <ExplorePage projectId={projectId} onGoHome={goHome} onSelectProject={openCase} />;
  }
  return <HomePage onOpenProject={openCase} />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router />
      </AuthProvider>
    </QueryClientProvider>
  );
}
