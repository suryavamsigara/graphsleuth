import os
from functools import lru_cache
from dotenv import load_dotenv
from supabase import Client, create_client

from engine.graph.knowledge_graph import KnowledgeGraph
from engine.extraction.extractor import EntityExtractor
from engine.ingestion.pipeline import IngestionPipeline
from engine.embeddings.encoder import LocalEncoder, EmbeddingEncoder
from engine.agent.reasoner_async import AsyncGraphReasoner
from storage.supabase.graph_store import SupabaseGraphStore
from storage.supabase.vector_store import SupabaseVectorStore
from storage.supabase.file_store import SupabaseFileStore
from apps.api.core.async_engine import AsyncEngine

load_dotenv()


@lru_cache
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY required")
    return create_client(url, key)


@lru_cache
def get_graph_store() -> SupabaseGraphStore:
    return SupabaseGraphStore(client=get_supabase_client())


@lru_cache
def get_vector_store() -> SupabaseVectorStore:
    return SupabaseVectorStore(client=get_supabase_client())


@lru_cache
def get_file_store() -> SupabaseFileStore:
    return SupabaseFileStore(client=get_supabase_client(), bucket="documents")


@lru_cache
def get_encoder() -> EmbeddingEncoder:
    return LocalEncoder(
        model_name="MinishLab/potion-retrieval-32M",
        dimensionality=384,
    )


@lru_cache
def get_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        store=get_graph_store(),
        vector_store=get_vector_store(),
        encoder=get_encoder(),
        min_entry_score=float(os.getenv("MIN_ENTRY_SCORE", "0.30")),
        guided_traversal_min_score=float(os.getenv("GUIDED_MIN_SCORE", "0.20")),
        beam_width=int(os.getenv("BEAM_WIDTH", "3")),
    )


@lru_cache
def get_agent() -> AsyncGraphReasoner:
    return AsyncGraphReasoner(
        kg=get_knowledge_graph(),
        encoder=get_encoder(),
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_openai=os.getenv("USE_OPENAI", "true").lower() == "true",
        max_evidence_chunks=int(os.getenv("MAX_EVIDENCE_CHUNKS", "12")),
        top_k=int(os.getenv("TOP_K", "5")),
    )


@lru_cache
def get_extractor() -> EntityExtractor:
    return EntityExtractor(
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_local=os.getenv("USE_LOCAL_LLM", "false").lower() == "true",
        encoder=get_encoder(),
    )


@lru_cache
def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        kg=get_knowledge_graph(),
        extractor=get_extractor(),
    )


@lru_cache
def get_engine() -> AsyncEngine:
    return AsyncEngine(
        kg=get_knowledge_graph(),
        pipeline=get_ingestion_pipeline(),
        agent=get_agent(),
        file_store=get_file_store(),
    )