import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import ChatPage from "./pages/ChatPage";
import IngestPage from "./pages/IngestPage";
import ExplorePage from "./pages/ExplorePage";
import EvidencePage from "./pages/EvidencePage";

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/ingest" element={<IngestPage />} />
        <Route path="/explore" element={<ExplorePage />} />
        <Route path="/evidence/:id" element={<EvidencePage />} />
      </Routes>
    </Layout>
  );
}