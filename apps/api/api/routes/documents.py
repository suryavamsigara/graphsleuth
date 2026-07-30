import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, BackgroundTasks

from apps.api.dependencies import get_file_store, get_ingestion_pipeline

router = APIRouter()


@router.post("/upload")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    file_store = get_file_store()
    pipeline = get_ingestion_pipeline()

    suffix = Path(file.filename).suffix
    local_path = f"/tmp/{uuid.uuid4()}{suffix}"

    with open(local_path, "wb") as f:
        f.write(await file.read())

    storage_path = f"uploads/{uuid.uuid4()}{suffix}"
    public_url = file_store.upload(local_path, storage_path)

    background_tasks.add_task(_ingest, local_path, file.filename)

    return {"document_id": None, "storage_path": storage_path, "url": public_url}


def _ingest(local_path: str, file_name: str):
    pipeline = get_ingestion_pipeline()
    result = pipeline.ingest_file(local_path, file_name)
    print(f"Ingestion result: {result}")