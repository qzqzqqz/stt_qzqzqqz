# Task 8: 下载功能 — 多格式生成 + zip 打包 + 原始音频

> 所属阶段: 阶段二：后端核心功能


**Goal:** 实现转录结果的多种格式下载，支持 JSON、TXT、SRT、VTT 字幕格式，以及 ZIP 打包（含所有格式 + 原始音频）。

**Files:**
- Create: `backend/app/services/export.py` — 格式转换核心服务
- Modify: `backend/app/api/v1/transcription.py` — 添加下载端点

- [x] **Step 1: 创建 export.py 格式转换服务**

```python
# backend/app/services/export.py
"""转录结果导出服务 — 支持 JSON、TXT、SRT、VTT、ZIP 多种格式."""

import io
import json
import zipfile
from datetime import timedelta

from app.models.transcription import Transcription


def _seconds_to_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """秒数转 VTT 时间格式 HH:MM:SS.mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def generate_json(transcription: Transcription) -> bytes:
    data = {
        "filename": transcription.filename,
        "model": transcription.model_used,
        "language": transcription.language,
        "duration": transcription.duration,
        "segments": transcription.result_json.get("segments", []) if transcription.result_json else [],
        "metadata": {k: v for k, v in (transcription.result_json or {}).items() if k != "segments"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def generate_txt(transcription: Transcription) -> bytes:
    lines = []
    lines.append("=" * 80)
    lines.append(f"音频文件: {transcription.filename}")
    lines.append(f"转录模型: {transcription.model_used}")
    lines.append(f"语言: {transcription.language or '未知'}")
    lines.append("=" * 80)
    lines.append("")

    for seg in _get_segments(transcription):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        lines.append(f"[{start} - {end}] {seg['speaker']}:")
        lines.append(seg["text"])
        lines.append("")

    lines.append("=" * 80)
    lines.append("完整文本:")
    lines.append("=" * 80)
    lines.append(transcription.result_text or "")
    return "\n".join(lines).encode("utf-8")


def generate_srt(transcription: Transcription) -> bytes:
    segments = _get_segments(transcription)
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(f"{seg['speaker']}: {seg['text']}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def generate_vtt(transcription: Transcription) -> bytes:
    segments = _get_segments(transcription)
    lines = [f"WEBVTT - {transcription.filename}", ""]
    for seg in segments:
        start = _seconds_to_vtt_time(seg["start"])
        end = _seconds_to_vtt_time(seg["end"])
        lines.append(f"{start} --> {end}")
        lines.append(f"<v {seg['speaker']}>{seg['text']}</v>")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def generate_zip(transcription: Transcription) -> bytes:
    buffer = io.BytesIO()
    base_name = transcription.filename.rsplit(".", 1)[0]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.json", generate_json(transcription))
        zf.writestr(f"{base_name}.txt", generate_txt(transcription))
        zf.writestr(f"{base_name}.srt", generate_srt(transcription))
        zf.writestr(f"{base_name}.vtt", generate_vtt(transcription))
        import os
        if os.path.exists(transcription.file_path):
            zf.write(transcription.file_path, arcname=transcription.filename)
    return buffer.getvalue()


def _get_segments(transcription: Transcription) -> list[dict]:
    if not transcription.result_json:
        return []
    return [
        {
            "start": seg.get("start_time", 0.0),
            "end": seg.get("end_time", 0.0),
            "speaker": f"Speaker {seg.get('speaker_id', 'Unknown')}",
            "text": seg.get("text", "").strip(),
        }
        for seg in transcription.result_json.get("segments", [])
    ]


_FORMAT_MAP = {
    "json": ("application/json", generate_json),
    "txt": ("text/plain; charset=utf-8", generate_txt),
    "srt": ("text/plain; charset=utf-8", generate_srt),
    "vtt": ("text/vtt; charset=utf-8", generate_vtt),
    "zip": ("application/zip", generate_zip),
}


def export_transcription(transcription: Transcription, format: str) -> tuple[str, bytes]:
    fmt = format.lower()
    if fmt not in _FORMAT_MAP:
        raise ValueError(f"不支持的格式: {format}。支持: {', '.join(_FORMAT_MAP.keys())}")
    if not transcription.result_json and fmt != "zip":
        raise ValueError("转录结果数据不可用")
    mimetype, generator = _FORMAT_MAP[fmt]
    return mimetype, generator(transcription)
```

> **设计说明:**
> - ZIP 使用 `io.BytesIO` 在内存中构建，不落磁盘临时文件
> - SRT 时间格式 `HH:MM:SS,mmm`，VTT 时间格式 `HH:MM:SS.mmm`（毫秒分隔符差异）
> - 所有生成函数接收 `Transcription` ORM 对象，统一从 `result_json` 提取 segments

- [x] **Step 2: 添加 download 端点到 transcription.py**

```python
# backend/app/api/v1/transcription.py
import io
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

# ... 已有导入
from app.services.export import export_transcription


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

    base_name = os.path.splitext(transcription.filename)[0]
    download_filename = f"{base_name}.{format.lower()}"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=mimetype,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )
```

> **设计说明:**
> - 端点返回 `StreamingResponse`，流式传输避免大文件占用过多内存
> - 仅 `completed` 状态可下载，防止下载不完整结果
> - `Content-Disposition: attachment` 强制浏览器下载而非预览
> - ZIP 中原始音频文件不存在时自动跳过，不影响文本格式打包

- [x] **Step 3: 提交**

```bash
git add app/services/export.py app/api/v1/transcription.py
git commit -m "feat(task8): add multi-format transcription download (json, txt, srt, vtt, zip)"
```

---

## 阶段三：前端基础
