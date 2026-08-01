import os
import uuid
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException

from apps.api.core.async_engine import AsyncEngine
from apps.api.dependencies import get_engine_for_read, get_engine_for_write
from apps.api.core.project_context import require_project_owner
from apps.api.core.projects_store import Project
from apps.api.api.schemas.documents import DocumentUploadResponse, DocumentListItem

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    project: Project = Depends(require_project_owner),
    engine: AsyncEngine = Depends(get_engine_for_write),
):
    """Upload a file, ingest into graph, archive to Supabase storage."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate extension
    suffix = Path(file.filename).suffix.lower()
    supported = {".txt", ".md", ".py", ".pdf"}
    if suffix not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {supported}",
        )

    # Save to temp file
    temp_dir = tempfile.mkdtemp(prefix="graphsleuth_")
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}{suffix}")

    try:
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Ingest into knowledge graph (already scoped to `project` via the
        # per-project engine returned by get_engine_for_write)
        result = await engine.ingest_file(temp_path, file.filename)

        # Archive original to Supabase if ingestion succeeded — namespaced
        # under the project so two projects can't collide on storage paths
        if result.get("success") and result.get("document_id"):
            file_store = engine.file_store
            storage_path = f"documents/{project.id}/{result['document_id']}/{file.filename}"
            await file_store.upload(temp_path, storage_path)

        return DocumentUploadResponse(
            success=result.get("success", False),
            document_id=result.get("document_id"),
            file_name=file.filename,
            chunks_processed=result.get("chunks_processed", 0),
            nodes_created=result.get("nodes_created", 0),
            edges_created=result.get("edges_created", 0),
            error=result.get("error"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temp
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)


@router.get("/", response_model=list[DocumentListItem])
async def list_documents(engine: AsyncEngine = Depends(get_engine_for_read)):
    docs = await engine.list_documents()
    return [
        DocumentListItem(
            id=d.id,
            name=d.name,
            path=d.path,
            ingested_at=d.ingested_at,
        )
        for d in docs
    ]


@router.get("/{doc_id}")
async def get_document(doc_id: str, engine: AsyncEngine = Depends(get_engine_for_read)):
    doc = await engine.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {
        "id": doc.id,
        "name": doc.name,
        "path": doc.path,
        "checksum": doc.checksum,
        "ingested_at": doc.ingested_at,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    project: Project = Depends(require_project_owner),
    engine: AsyncEngine = Depends(get_engine_for_write),
):
    # Will cascade delete in graph_store
    raise HTTPException(status_code=501, detail="Not yet implemented")