import logging
from datetime import datetime, timezone

from celery import shared_task
from celery.signals import worker_process_init

from app.config import settings
from app.database import TranscriptionStatus
from app.database_sync import SessionLocal
from app.models.transcription import Transcription

logger = logging.getLogger(__name__)

# 全局模型引用，由 worker_process_init 预加载
_stt_model = None


@worker_process_init.connect
def load_stt_model(**kwargs):
    """每个 Worker 子进程启动时预加载 mlx-audio 模型。

    Celery 默认使用 prefork pool（尤其 macOS），每个子进程 fork 后都需要
    独立加载模型。模型加载耗时较长（下载+初始化），但只发生一次。
    """
    global _stt_model
    logger.info("Loading STT model: %s", settings.STT_MODEL)
    from mlx_audio.stt.utils import load

    _stt_model = load(settings.STT_MODEL)
    logger.info("STT model loaded successfully")


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def transcribe_audio(self, transcription_id: str):
    """执行音频转录任务。

    状态流转:
        pending → processing → completed / failed

    Args:
        transcription_id: Transcription 记录的 UUID（字符串形式）
    """
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

        # 2. 调用 mlx-audio 执行转录
        result = _stt_model.generate(
            audio=transcription.file_path,
            max_tokens=8192,
            temperature=0.0,
            verbose=False,
        )

        # 3. 保存结果到数据库
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
