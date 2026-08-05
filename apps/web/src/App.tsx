import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./styles/tokens.css";
import { AuthProvider } from "./lib/authContext";
import HomePage from "./pages/HomePage";
import ExplorePage from "./pages/ExplorePage";
import AuthPage from "./pages/AuthPage";
import ProfilePage from "./pages/ProfilePage";

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

  const projectMatch = hash.match(/^#\/project\/(.+)$/);
  const isLogin = hash === "#/login";
  const isRegister = hash === "#/register";
  const isProfile = hash === "#/profile";

  return {
    projectId: projectMatch ? decodeURIComponent(projectMatch[1]) : null,
    authMode: isLogin ? ("login" as const) : isRegister ? ("register" as const) : null,
    isProfile,
  };
}

function Router() {
  const { projectId, authMode, isProfile } = useRoute();

  const goHome = () => {
    window.location.hash = "";
  };
  const openProject = (id: string) => {
    window.location.hash = `#/project/${encodeURIComponent(id)}`;
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

  if (isProfile) {
    return <ProfilePage onGoHome={goHome} />;
  }

  if (projectId) {
    return <ExplorePage projectId={projectId} onGoHome={goHome} onSelectProject={openProject} />;
  }
  return <HomePage onOpenProject={openProject} />;
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
