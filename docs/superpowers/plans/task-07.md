# Task 7: 转录结果 API — 列表/详情/状态查询

> 所属阶段: 阶段二：后端核心功能


**Goal:** 实现转录任务的列表查询（分页）、详情查询和状态查询接口。

**Files:**
- Modify: `backend/app/schemas/transcription.py` — 新增详情/列表响应 Schema
- Modify: `backend/app/api/v1/transcription.py` — 新增列表和详情端点

- [x] **Step 1: 更新 Transcription schemas**

新增 `TranscriptionDetailResponse`（详情视图，含完整结果数据）和 `TranscriptionListResponse`（分页包装）：

```python
# backend/app/schemas/transcription.py
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
```

- [x] **Step 2: 添加列表和详情 API 端点**

```python
# backend/app/api/v1/transcription.py
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.database import TranscriptionStatus
from app.models.transcription import Transcription
from app.models.user import User
from app.schemas.transcription import (
    TranscriptionDetailResponse,
    TranscriptionListResponse,
    TranscriptionResponse,
)
from app.services.export import export_transcription
from app.services.upload import save_upload_file
from app.tasks.transcription import transcribe_audio

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(...):
    """上传音频文件并创建转录任务."""
    ...


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: TranscriptionStatus | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的转录任务列表（分页）."""
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    count_query = select(func.count()).select_from(Transcription).where(Transcription.user_id == current_user.id)

    if status:
        query = query.where(Transcription.status == status)
        count_query = count_query.where(Transcription.status == status)

    query = query.order_by(Transcription.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    pages = (total + page_size - 1) // page_size

    return TranscriptionListResponse(
        items=list(items), total=total, page=page, page_size=page_size, pages=pages,
    )


@router.get("/{transcription_id}", response_model=TranscriptionDetailResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询单个转录任务详情."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    return transcription
```

> **设计说明:**
> - 列表端点仅返回基础字段，不含 `result_json`/`result_text`，避免大字段拖慢列表加载
> - 详情端点返回完整数据，供前端展示转录结果和下载
> - 分页参数限制 `page_size` 最大 100，防止恶意大分页
> - 两个端点均通过 `user_id == current_user.id` 鉴权，只能访问自己的记录

- [x] **Step 3: 提交**

```bash
git add app/api/v1/transcription.py app/schemas/transcription.py
git commit -m "feat(task7): add transcription list and detail API endpoints"
```

---
