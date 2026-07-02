"""知识库相关 Pydantic Schema"""
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: int
    filename: str
    original_name: str
    file_type: str
    file_size: int
    chunk_count: int
    char_count: int
    status: str
    error_message: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[DocumentResponse]


class KnowledgeStats(BaseModel):
    total_documents: int
    total_chunks: int
    total_chars: int
    completed_documents: int
    processing_documents: int
    failed_documents: int
