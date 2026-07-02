"""问答相关 Pydantic Schema"""
from pydantic import BaseModel, Field
from typing import Optional


class SessionCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class SessionResponse(BaseModel):
    id: int
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0

    model_config = {"from_attributes": True}


class SendMessage(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="用户问题")


class SourceInfo(BaseModel):
    doc_name: str
    content: str
    score: float


class MessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    sources: Optional[list[SourceInfo]] = None
    created_at: str

    model_config = {"from_attributes": True}


class ChatHistoryResponse(BaseModel):
    session: SessionResponse
    messages: list[MessageResponse]
