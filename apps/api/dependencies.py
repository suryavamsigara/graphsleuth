import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from functools import lru_cache
from supabase import Client, create_client

from engine.graph.knowledge_graph import KnowledgeGraph
from engine.extraction.extractor import EntityExtractor
from engine.agent.reasoner import GraphReasoner
from engine.ingestion.pipeline import IngestionPipeline
from engine.embeddings.encoder import LocalEncoder, EmbeddingEncoder
from storage.supabase.graph_store import SupabaseGraphStore
from storage.supabase.vector_store import SupabaseVectorStore
from storage.supabase.file_store import SupabaseFileStore

load_dotenv()

_conn = psycopg.connect("postgresql://graphsleuth_user:graphsleuthpassword@localhost:5432/graphsleuth", row_factory=dict_row)

@lru_cache
def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
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
    return LocalEncoder(model_name="MinishLab/potion-retrieval-32M", dimensionality=384)


@lru_cache
def get_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        store=get_graph_store(),
        vector_store=get_vector_store(),
        encoder=get_encoder(),
        min_entry_score=float(os.getenv("MIN_ENTRY_SCORE", "0.30")),
        guided_traversal_min_score=float(os.getenv("GUIDED_MIN_SCORE", "0.20")),
        beam_width=int(os.getenv("BEAM_WIDTH", "5")),
    )

@lru_cache
def get_agent() -> GraphReasoner:
    kg = get_knowledge_graph()
    return GraphReasoner(
        kg=kg,
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_openai=True,
        max_evidence_chunks=int(os.getenv("MAX_EVIDENCE_CHUNKS", "12")),
        top_k=int(os.getenv("TOP_K", "5")),
    )

@lru_cache
def get_extractor() -> EntityExtractor:
    return EntityExtractor(
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_local=os.getenv("USE_LOCAL_LLM", "false").lower() == "true",
        embedding_model=get_encoder(),
    )

@lru_cache
def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        kg=get_knowledge_graph(),
        extractor=get_extractor(),
    )
