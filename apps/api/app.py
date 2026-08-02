from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.api.routes import documents, query, graph, health, projects, chat


@asynccontextmanager
async def lifespan(app: FastAPI):
    from apps.api.dependencies import get_supabase_client
    _ = get_supabase_client()
    yield
    # Shutdown: close stores
    from apps.api.dependencies import get_graph_store, get_vector_store
    get_graph_store().close()
    get_vector_store().close()


app = FastAPI(
    title="GraphSleuth API",
    description="Knowledge graph RAG",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(graph.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"message": "GraphSleuth API", "docs": "/docs"}