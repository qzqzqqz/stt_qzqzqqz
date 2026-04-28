import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.database import TranscriptionStatus


class TranscriptionBase(BaseModel):
    filename: str
    language: str | None = None


class TranscriptionCreate(TranscriptionBase):
    pass


class TranscriptionResponse(TranscriptionBase):
    """列表视图响应 — 不包含完整结果数据."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_size: int
    duration: float | None = None
    status: TranscriptionStatus
    model_used: str
    created_at: datetime


class TranscriptionDetailResponse(TranscriptionResponse):
    """详情视图响应 — 包含完整转录结果."""

    result_json: dict | None = None
    result_text: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None


class TranscriptionListResponse(BaseModel):
    """分页列表响应."""

    items: list[TranscriptionResponse]
    total: int
    page: int
    page_size: int
    pages: int