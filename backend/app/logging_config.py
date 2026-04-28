import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    """配置应用日志：控制台 + 按组件文件输出 + 错误日志."""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 根 logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 避免重复添加 handler（如 reload 时）
    if root.handlers:
        return

    # 控制台处理器
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # 应用日志 -> app.log（绑定到 root，所有 INFO 级别日志都会写入）
    app_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    root.addHandler(app_handler)

    # Celery 任务日志 -> celery.log
    celery_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "celery.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    celery_handler.setFormatter(formatter)
    celery_logger = logging.getLogger("app.tasks")
    celery_logger.addHandler(celery_handler)
    celery_logger.setLevel(logging.INFO)

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
    root.addHandler(error_handler)
