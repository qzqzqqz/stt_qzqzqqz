import io
import logging
import os
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api.deps import get_current_user, get_db

logger = logging.getLogger(__name__)
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


@router.post("", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
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

    # 触发异步转录任务
    transcribe_audio.delay(str(transcription.id))
    logger.info("Transcription created: %s (%s)", transcription.id, transcription.filename)

    return transcription


@router.get("", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: TranscriptionStatus | None = Query(None, description="按状态筛选"),
    search: str | None = Query(None, description="按文件名搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的转录任务列表（分页）."""
    # 构建查询
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    count_query = select(func.count()).select_from(Transcription).where(Transcription.user_id == current_user.id)

    if status:
        query = query.where(Transcription.status == status)
        count_query = count_query.where(Transcription.status == status)

    if search:
        query = query.where(Transcription.filename.ilike(f"%{search}%"))
        count_query = count_query.where(Transcription.filename.ilike(f"%{search}%"))

    # 按创建时间倒序
    query = query.order_by(Transcription.created_at.desc())

    # 分页
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    items = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    pages = (total + page_size - 1) // page_size

    return TranscriptionListResponse(
        items=list(items),
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
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


@router.get("/{transcription_id}/download")
async def download_transcription(
    transcription_id: uuid.UUID,
    format: str = Query(..., description="导出格式: json, txt, srt, vtt, zip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载转录结果（多种格式）."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.completed:
        raise HTTPException(
            status_code=400,
            detail=f"Transcription not completed (current status: {transcription.status.value})",
        )

    try:
        mimetype, content = export_transcription(transcription, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # 生成下载文件名（RFC 5987 编码，支持中文）
    base_name = os.path.splitext(transcription.filename)[0]
    extension = format.lower()
    download_filename = f"{base_name}.{extension}"
    encoded_filename = quote(download_filename)

    return StreamingResponse(
        io.BytesIO(content),
        media_type=mimetype,
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{download_filename}\"; "
                f"filename*=UTF-8''{encoded_filename}"
            ),
        },
    )


@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除转录记录及其关联的音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # 删除磁盘上的音频文件
    if os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)

    await db.delete(transcription)
    await db.commit()


@router.get("/{transcription_id}/audio")
async def download_audio(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载原始音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not os.path.exists(transcription.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        transcription.file_path,
        filename=transcription.filename,
        media_type="application/octet-stream",
    )
