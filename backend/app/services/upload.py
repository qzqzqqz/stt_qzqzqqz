import os
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