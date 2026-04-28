"""转录结果导出服务 — 支持 JSON、TXT、SRT、VTT、ZIP 多种格式."""

import io
import json
import zipfile
from datetime import timedelta

from app.models.transcription import Transcription


# ── 时间转换工具 ───────────────────────────────────────────────


def _seconds_to_srt_time(seconds: float) -> str:
    """将秒数转换为 SRT 时间格式 HH:MM:SS,mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """将秒数转换为 VTT 时间格式 HH:MM:SS.mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


# ── 各格式生成函数 ─────────────────────────────────────────────


def generate_json(transcription: Transcription) -> bytes:
    """生成 JSON 格式导出文件."""
    data = {
        "filename": transcription.filename,
        "model": transcription.model_used,
        "language": transcription.language,
        "duration": transcription.duration,
        "segments": transcription.result_json.get("segments", []) if transcription.result_json else [],
        "metadata": {
            "prompt_tokens": transcription.result_json.get("prompt_tokens") if transcription.result_json else None,
            "generation_tokens": transcription.result_json.get("generation_tokens") if transcription.result_json else None,
            "total_tokens": transcription.result_json.get("total_tokens") if transcription.result_json else None,
            "prompt_tps": transcription.result_json.get("prompt_tps") if transcription.result_json else None,
            "generation_tps": transcription.result_json.get("generation_tps") if transcription.result_json else None,
            "total_time": transcription.result_json.get("total_time") if transcription.result_json else None,
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def generate_txt(transcription: Transcription) -> bytes:
    """生成 TXT 格式导出文件."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"音频文件: {transcription.filename}")
    lines.append(f"转录模型: {transcription.model_used}")
    lines.append(f"语言: {transcription.language or '未知'}")
    lines.append(f"音频时长: {transcription.duration:.1f}s" if transcription.duration else "音频时长: 未知")
    lines.append(f"转录时间: {transcription.completed_at.isoformat() if transcription.completed_at else 'N/A'}")
    lines.append("=" * 80)
    lines.append("")

    segments = _get_segments(transcription)
    for seg in segments:
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        speaker = seg["speaker"]
        text = seg["text"]
        lines.append(f"[{start} - {end}] {speaker}:")
        lines.append(text)
        lines.append("")

    lines.append("=" * 80)
    lines.append("完整文本:")
    lines.append("=" * 80)
    lines.append(transcription.result_text or "")
    lines.append("")

    return "\n".join(lines).encode("utf-8")


def generate_srt(transcription: Transcription) -> bytes:
    """生成 SRT 字幕格式文件."""
    segments = _get_segments(transcription)
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        speaker = seg["speaker"]
        text = seg["text"]
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(f"{speaker}: {text}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def generate_vtt(transcription: Transcription) -> bytes:
    """生成 WebVTT 字幕格式文件."""
    segments = _get_segments(transcription)
    lines = [f"WEBVTT - {transcription.filename}", ""]
    lines.append(f"NOTE 转录模型: {transcription.model_used}")
    lines.append(f"NOTE 语言: {transcription.language or '未知'}")
    lines.append("")

    for seg in segments:
        start = _seconds_to_vtt_time(seg["start"])
        end = _seconds_to_vtt_time(seg["end"])
        speaker = seg["speaker"]
        text = seg["text"]
        lines.append(f"{start} --> {end}")
        lines.append(f"<v {speaker}>{text}</v>")
        lines.append("")

    return "\n".join(lines).encode("utf-8")


def generate_zip(transcription: Transcription) -> bytes:
    """生成 ZIP 包，包含所有格式 + 原始音频."""
    buffer = io.BytesIO()
    base_name = _get_base_name(transcription.filename)

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # 各格式文本文件
        zf.writestr(f"{base_name}.json", generate_json(transcription))
        zf.writestr(f"{base_name}.txt", generate_txt(transcription))
        zf.writestr(f"{base_name}.srt", generate_srt(transcription))
        zf.writestr(f"{base_name}.vtt", generate_vtt(transcription))

        # 原始音频文件（如存在）
        import os
        if os.path.exists(transcription.file_path):
            zf.write(transcription.file_path, arcname=transcription.filename)

    return buffer.getvalue()


# ── 辅助函数 ───────────────────────────────────────────────────


def _get_segments(transcription: Transcription) -> list[dict]:
    """从 result_json 中提取标准化的 segment 列表."""
    if not transcription.result_json:
        return []

    raw_segments = transcription.result_json.get("segments", [])
    segments = []
    for seg in raw_segments:
        segments.append({
            "start": seg.get("start_time", 0.0),
            "end": seg.get("end_time", 0.0),
            "speaker": f"Speaker {seg.get('speaker_id', 'Unknown')}",
            "text": seg.get("text", "").strip(),
        })
    return segments


def _get_base_name(filename: str) -> str:
    """从原始文件名中提取基础名（去除扩展名）."""
    import os
    return os.path.splitext(filename)[0]


# ── 主分发函数 ─────────────────────────────────────────────────


_FORMAT_MIME_TYPES = {
    "json": "application/json",
    "txt": "text/plain; charset=utf-8",
    "srt": "text/plain; charset=utf-8",
    "vtt": "text/vtt; charset=utf-8",
    "zip": "application/zip",
}

_FORMAT_GENERATORS = {
    "json": generate_json,
    "txt": generate_txt,
    "srt": generate_srt,
    "vtt": generate_vtt,
    "zip": generate_zip,
}


def export_transcription(transcription: Transcription, format: str) -> tuple[str, bytes]:
    """根据格式导出转录结果.

    Args:
        transcription: Transcription ORM 对象
        format: 导出格式，支持 json/txt/srt/vtt/zip

    Returns:
        (mimetype, content_bytes)

    Raises:
        ValueError: 格式不支持或结果数据不可用
    """
    fmt = format.lower()
    if fmt not in _FORMAT_GENERATORS:
        supported = ", ".join(_FORMAT_GENERATORS.keys())
        raise ValueError(f"不支持的格式: {format}。支持: {supported}")

    if not transcription.result_json and fmt != "zip":
        raise ValueError("转录结果数据不可用")

    generator = _FORMAT_GENERATORS[fmt]
    content = generator(transcription)
    mimetype = _FORMAT_MIME_TYPES[fmt]
    return mimetype, content