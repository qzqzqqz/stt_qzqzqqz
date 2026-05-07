import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import soundfile as sf
from celery import shared_task

from app.config import settings
from app.database import TranscriptionStatus
from app.database_sync import SessionLocal
from app.models.transcription import Transcription

logger = logging.getLogger(__name__)

# 全局模型引用，按需加载（macOS Metal 在 prefork 中不可用，使用 solo pool）
_stt_model = None


def _load_stt_model():
    """按需加载 mlx-audio 模型，优先使用本地缓存。"""
    global _stt_model
    if _stt_model is not None:
        return _stt_model

    # 强制离线模式，避免 HuggingFace Hub 网络请求超时
    os.environ["HF_HUB_OFFLINE"] = "1"

    logger.info("Loading STT model: %s", settings.STT_MODEL)
    from mlx_audio.stt.utils import load

    # 优先从 HuggingFace 本地缓存加载
    cache_dir = Path.home() / ".cache/huggingface/hub"
    model_cache = cache_dir / f"models--{settings.STT_MODEL.replace('/', '--')}"
    snapshots = list((model_cache / "snapshots").glob("*"))

    if snapshots:
        local_path = snapshots[0]
        logger.info("Using cached model at %s", local_path)
        _stt_model = load(local_path)
    else:
        logger.info("No local cache found, downloading from HuggingFace...")
        _stt_model = load(settings.STT_MODEL)

    logger.info("STT model loaded successfully")
    return _stt_model


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def transcribe_audio(self, transcription_id: str):
    """执行音频转录任务。

    状态流转:
        pending → processing → completed / failed

    Args:
        transcription_id: Transcription 记录的 UUID（字符串形式）
    """
    # 按需加载模型（macOS Metal 在 prefork 中不可用，solo pool 下在任务中加载）
    model = _load_stt_model()

    db = SessionLocal()
    try:
        # 1. 查询记录，状态设为 processing
        transcription = (
            db.query(Transcription)
            .filter(Transcription.id == transcription_id)
            .first()
        )
        if not transcription:
            logger.error("Transcription %s not found", transcription_id)
            return

        transcription.status = TranscriptionStatus.processing
        db.commit()

        self.update_state(state="PROCESSING", meta={"status": "processing"})
        logger.info("Started transcribing %s", transcription_id)

        # 2. 获取音频时长并填充 duration 字段
        try:
            audio_info = sf.info(transcription.file_path)
            duration_seconds = audio_info.duration
            transcription.duration = int(duration_seconds)
            db.commit()
            logger.info("Audio duration: %.1fs", duration_seconds)
        except Exception:
            duration_seconds = 0
            logger.warning("Could not determine audio duration")

        # 3. 根据音频时长动态计算 max_tokens（留 1.5x 余量，上限 131072）
        duration_minutes = duration_seconds / 60
        estimated_tokens = int(duration_minutes * 500 * 1.5)
        max_tokens = max(8192, min(estimated_tokens, 131072))
        logger.info("max_tokens set to %d (duration: %.1f min)", max_tokens, duration_minutes)

        # 4. 调用 mlx-audio 执行转录
        result = model.generate(
            audio=transcription.file_path,
            max_tokens=max_tokens,
            temperature=0.0,
            verbose=False,
        )

        # 5. 保存结果到数据库
        transcription.result_text = result.text
        transcription.result_json = {
            "segments": result.segments,
            "language": result.language,
            "prompt_tokens": result.prompt_tokens,
            "generation_tokens": result.generation_tokens,
            "total_tokens": result.total_tokens,
            "prompt_tps": result.prompt_tps,
            "generation_tps": result.generation_tps,
            "total_time": result.total_time,
        }
        transcription.status = TranscriptionStatus.completed
        transcription.completed_at = datetime.now(timezone.utc)
        db.commit()

        self.update_state(state="SUCCESS", meta={"status": "completed"})
        logger.info(
            "Transcription %s completed in %.2fs",
            transcription_id,
            result.total_time,
        )

    except Exception as exc:
        db.rollback()
        logger.exception("Transcription %s failed: %s", transcription_id, exc)

        # 更新失败状态
        transcription = (
            db.query(Transcription)
            .filter(Transcription.id == transcription_id)
            .first()
        )
        if transcription:
            transcription.status = TranscriptionStatus.failed
            transcription.error_message = str(exc)
            db.commit()

        # 触发重试（最多 2 次，间隔 60 秒）
        raise self.retry(exc=exc)
    finally:
        db.close()
