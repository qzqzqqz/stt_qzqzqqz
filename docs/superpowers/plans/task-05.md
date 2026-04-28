# Task 5: 文件上传 — 接收音频 + 存储 + 创建记录

> 所属阶段: 阶段二：后端核心功能


**Goal:** 实现音频文件上传接口，验证格式与大小，保存到本地目录，并在数据库中创建对应的 Transcription 记录。

**Files:**
- Create: `backend/app/schemas/transcription.py`
- Create: `backend/app/services/upload.py`
- Create: `backend/app/api/v1/transcription.py`
- Modify: `backend/app/api/v1/__init__.py` — 注册转录路由
- Modify: `backend/app/main.py` — 确保上传目录存在

- [x] **Step 1: 创建 Transcription Schemas**

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
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_size: int
    duration: float | None = None
    status: TranscriptionStatus
    model_used: str
    created_at: datetime
```

- [x] **Step 2: 创建文件上传服务**

```python
# backend/app/services/upload.py
import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = settings.ALLOWED_AUDIO_EXTENSIONS
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_file(file: UploadFile) -> None:
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 大小校验在读取后执行（UploadFile 不预读大小）


async def save_upload_file(file: UploadFile, user_id: str) -> tuple[str, int]:
    """保存上传文件，返回 (文件路径, 文件大小)."""
    validate_file(file)

    ext = _get_extension(file.filename or "")
    file_name = f"{uuid.uuid4()}.{ext}"
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / file_name

    size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):
            size += len(chunk)
            if size > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB} MB",
                )
            buffer.write(chunk)

    return str(file_path), size
```

- [x] **Step 3: 创建转录上传路由**

```python
# backend/app/api/v1/transcription.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionResponse
from app.services.upload import save_upload_file

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    file: UploadFile = File(...),
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传音频文件并创建转录任务."""
    file_path, file_size = await save_upload_file(file, str(current_user.id))

    transcription = Transcription(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        language=language,
        status=TranscriptionStatus.pending,
        model_used=settings.STT_MODEL,
    )
    db.add(transcription)
    await db.commit()
    await db.refresh(transcription)
    return transcription
```

- [x] **Step 4: 注册转录路由到 v1 聚合器**

```python
# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import auth, transcription

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(transcription.router)
```

- [x] **Step 5: 确保上传目录在应用启动时存在**

```python
# backend/app/main.py — 在 app 创建后添加
from pathlib import Path
from app.config import settings

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
```

> **设计说明:**
> - 文件按用户 ID 分目录存储：`uploads/{user_id}/{uuid}.{ext}`，避免文件名冲突
> - 流式读取 + 边读边校验大小，避免大文件占用过多内存
> - 仅保存原始文件名到数据库，实际存储使用 UUID 命名，防止路径遍历攻击
> - 创建记录时状态为 `pending`，等待 Celery Worker 处理转录

---
