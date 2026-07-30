import os
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from engine.graph.knowledge_graph import KnowledgeGraph
from engine.extraction.extractor import EntityExtractor
from engine.agent.reasoner import GraphReasoner
from engine.ingestion.pipeline import IngestionPipeline
from engine.embeddings.encoder import LocalEncoder, EmbeddingEncoder
from storage.postgres.graph_store import PostgresGraphStore
from storage.postgres.vector_store import PostgresVectorStore

load_dotenv()

_conn = psycopg.connect("postgresql://graphsleuth_user:graphsleuthpassword@localhost:5432/graphsleuth", row_factory=dict_row)


def get_graph_store() -> PostgresGraphStore:
    return PostgresGraphStore(_conn)

def get_vector_store() -> PostgresVectorStore:
    return PostgresVectorStore(_conn)

def get_encoder() -> EmbeddingEncoder:
    return LocalEncoder(dimensionality=384)

def get_knowledge_graph() -> KnowledgeGraph:
    return KnowledgeGraph(
        store=get_graph_store(),
        vector_store=get_vector_store(),
        encoder=get_encoder(),
        min_entry_score=float(os.getenv("MIN_ENTRY_SCORE", "0.30")),
        guided_traversal_min_score=float(os.getenv("GUIDED_MIN_SCORE", "0.20")),
        beam_width=int(os.getenv("BEAM_WIDTH", "5")),
    )

def get_agent() -> GraphReasoner:
    kg = get_knowledge_graph()
    return GraphReasoner(
        kg=kg,
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_openai=True,
        max_evidence_chunks=int(os.getenv("MAX_EVIDENCE_CHUNKS", "12")),
        top_k=int(os.getenv("TOP_K", "5")),
    )

def get_extractor() -> EntityExtractor:
    return EntityExtractor(
        model_name=os.getenv("LLM_MODEL", "deepseek-v4-flash"),
        use_local=os.getenv("USE_LOCAL_LLM", "false").lower() == "true",
        embedding_model=get_encoder(),
    )

def get_ingestion_pipeline() -> IngestionPipeline:
    return IngestionPipeline(
        kg=get_knowledge_graph(),
        extractor=get_extractor(),
    )





def get_node_encoder() -> EmbeddingEncoder:
    """128-dim for nodes"""
    return LocalEncoder(
        model_name="MinishLab/potion-retrieval-32M",
        dimensionality=128,
    )

def get_chunk_encoder() -> EmbeddingEncoder:
    """384-dim for chunks"""
    return LocalEncoder(
        model_name="MinishLab/potion-retrieval-32M",
        dimensionality=384,
    )