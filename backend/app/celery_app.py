from celery import Celery

from app.config import settings
from app.logging_config import setup_logging

setup_logging()

celery_app = Celery(
    "stt_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.transcription"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,          # 单任务最大运行 1 小时（长音频需要）
    worker_prefetch_multiplier=1,  # 每个 worker 只预取 1 个任务，避免占用过多内存
)