from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.dependencies import get_knowledge_graph
from apps.api.api.routes import documents, query, graph, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    kg = get_knowledge_graph()
    print(f"Graph ready: {kg.get_metrics()}")
    yield


app = FastAPI(title="GraphSleuth API", lifespan=lifespan)

app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(query.router, prefix="/query", tags=["query"])
app.include_router(graph.router, prefix="/graph", tags=["graph"])
app.include_router(health.router, prefix="/health", tags=["health"])