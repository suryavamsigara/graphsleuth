import os
from functools import lru_cache
from dotenv import load_dotenv
from fastapi import Depends
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
from apps.api.core.project_context import get_current_project, require_project_owner
from apps.api.core.projects_store import Project

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
def get_extractor() -> EntityExtractor:
    return EntityExtractor(
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_local=os.getenv("USE_LOCAL_LLM", "false").lower() == "true",
        encoder=get_encoder(),
    )


# maxsize caps how many projects' graphs stay warm in memory at once
_PROJECT_CACHE_SIZE = int(os.getenv("PROJECT_CACHE_SIZE", "64"))


@lru_cache(maxsize=_PROJECT_CACHE_SIZE)
def get_knowledge_graph(project_id: str) -> KnowledgeGraph:
    return KnowledgeGraph(
        project_id=project_id,
        store=get_graph_store(),
        vector_store=get_vector_store(),
        encoder=get_encoder(),
        min_entry_score=float(os.getenv("MIN_ENTRY_SCORE", "0.30")),
        guided_traversal_min_score=float(os.getenv("GUIDED_MIN_SCORE", "0.20")),
        beam_width=int(os.getenv("BEAM_WIDTH", "3")),
    )


@lru_cache(maxsize=_PROJECT_CACHE_SIZE)
def get_agent(project_id: str) -> AsyncGraphReasoner:
    return AsyncGraphReasoner(
        kg=get_knowledge_graph(project_id),
        encoder=get_encoder(),
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_openai=os.getenv("USE_OPENAI", "true").lower() == "true",
        max_trace_chunks=int(os.getenv("MAX_EVIDENCE_CHUNKS", "12")),
        top_k=int(os.getenv("TOP_K", "5")),
    )


@lru_cache(maxsize=_PROJECT_CACHE_SIZE)
def get_ingestion_pipeline(project_id: str) -> IngestionPipeline:
    return IngestionPipeline(
        kg=get_knowledge_graph(project_id),
        extractor=get_extractor(),
    )


@lru_cache(maxsize=_PROJECT_CACHE_SIZE)
def get_engine(project_id: str) -> AsyncEngine:
    return AsyncEngine(
        kg=get_knowledge_graph(project_id),
        pipeline=get_ingestion_pipeline(project_id),
        agent=get_agent(project_id),
        file_store=get_file_store(),
    )


def get_engine_for_read(project: Project = Depends(get_current_project)) -> AsyncEngine:
    return get_engine(project.id)


def get_engine_for_write(project: Project = Depends(require_project_owner)) -> AsyncEngine:
    return get_engine(project.id)
