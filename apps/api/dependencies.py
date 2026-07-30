import os
from dotenv import load_dotenv

from engine.graph.knowledge_graph import KnowledgeGraph
from engine.agent.reasoner import GraphReasoner
from storage.postgres.graph_store import PostgresGraphStore
from model2vec import StaticModel

load_dotenv()

# Later will use FastAPI Depends with lifespan
_store: PostgresGraphStore | None = None
_kg: KnowledgeGraph | None = None

def get_graph_store() -> PostgresGraphStore:
    global _store
    if _store is None:
        _store = PostgresGraphStore(dsn = os.getenv("DATABASE"))
    return _store

def get_knowledge_graph() -> KnowledgeGraph:
    global _kg
    if _kg is None:
        embed = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M",
            dimensionality=128,
        )

        query = StaticModel.from_pretrained(
            "MinishLab/potion-retrieval-32M"
        )
        
        store = get_graph_store()
        _kg = KnowledgeGraph(
            store=store,
            embedding_model=embed,
            querying_model=query,
            min_entry_score=0.30,
            beam_width=5,
        )
    return _kg

def get_agent() -> GraphReasoner:
    kg = get_knowledge_graph()
    return GraphReasoner(
        kg=kg,
        model_name="deepseek-v4-flash",
        use_openai=True,
        max_evidence_chunks=12,
        top_k=5,
    )