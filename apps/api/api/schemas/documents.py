from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    success: bool
    document_id: str | None
    file_name: str
    chunks_processed: int
    nodes_created: int
    edges_created: int
    error: str | None = None

class DocumentListItem(BaseModel):
    id: str
    name: str
    path: str
    ingested_at: str

class DocumentDetailResponse(BaseModel):
    id: str
    name: str
    path: str
    checksum: str
    ingested_at: str
    chunks: list[dict]