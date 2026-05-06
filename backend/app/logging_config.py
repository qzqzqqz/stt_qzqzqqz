import logging
import logging.handlers
import uuid
from contextvars import ContextVar
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 协程安全的请求 ID 上下文变量
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """在每个日志记录中注入当前请求的 request_id."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


def setup_logging():
    """配置应用日志：控制台 + 按组件文件输出 + 错误日志."""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    request_id_filter = RequestIdFilter()

    # 根 logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 避免重复添加 handler（如 reload 时）
    if root.handlers:
        return

    # 过滤 SQLAlchemy 引擎噪音（保留 WARNING 以上：连接失败等）
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

    # 控制台处理器
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(request_id_filter)
    root.addHandler(console)

    # 应用日志 -> app.log
    app_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    app_handler.addFilter(request_id_filter)
    root.addHandler(app_handler)

    # 统一 uvicorn 访问日志格式
    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers = []
    uvicorn_access.addHandler(console)
    uvicorn_access.addHandler(app_handler)
    uvicorn_access.setLevel(logging.INFO)

    # Celery 任务日志 -> celery.log（不向上传播到 root，避免重复进入 app.log）
    celery_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "celery.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    celery_handler.setFormatter(formatter)
    celery_handler.addFilter(request_id_filter)
    celery_logger = logging.getLogger("app.tasks")
    celery_logger.addHandler(celery_handler)
    celery_logger.setLevel(logging.INFO)
    celery_logger.propagate = False

    # 错误日志（ERROR 以上，所有组件共用）-> error.log
    error_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "error.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    error_handler.addFilter(request_id_filter)
    root.addHandler(error_handler)