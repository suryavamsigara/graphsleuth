import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "./styles/tokens.css";
import ExplorePage from "./pages/ExplorePage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10_000 } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ExplorePage />
    </QueryClientProvider>
  );
}
