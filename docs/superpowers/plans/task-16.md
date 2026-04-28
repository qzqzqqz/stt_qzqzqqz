# Task 16: 日志配置 — 按组件分文件 + 按天轮转 + 自动清理

> 所属阶段: 阶段五：集成与收尾


**Goal:** 建立统一的后端日志系统，按组件（FastAPI / Celery）分文件输出，支持按天轮转、自动清理，方便排查问题和监控。

**Files:**
- Create: `backend/app/logging_config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`
- Modify: `backend/app/api/v1/*.py`
- Modify: `backend/.gitignore`

- [x] **Step 1: 创建日志配置模块 `logging_config.py`**

定义统一的日志格式、按天轮转的文件处理器（保留 7 天），输出到 `backend/logs/`：

```python
# backend/app/logging_config.py
import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging():
    """配置应用日志：控制台 + 按组件文件输出 + 错误日志"""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 根 logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # 控制台处理器
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    # FastAPI 应用日志 → app.log
    app_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "app.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    logging.getLogger("app").addHandler(app_handler)
    logging.getLogger("app").setLevel(logging.INFO)
    logging.getLogger("app").propagate = True

    # Celery 任务日志 → celery.log
    celery_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_DIR / "celery.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8",
    )
    celery_handler.setFormatter(formatter)
    logging.getLogger("app.tasks").addHandler(celery_handler)
    logging.getLogger("app.tasks").setLevel(logging.INFO)

    # 错误日志（ERROR 以上，所有组件共用）→ error.log
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
```

- [x] **Step 2: 在 `main.py` 启动时加载日志配置**

```python
from app.logging_config import setup_logging

setup_logging()
```

- [x] **Step 3: 在 `celery_app.py` 中加载日志配置**

确保 Celery Worker 启动时也使用相同的日志配置。

- [x] **Step 4: 为 API 路由模块添加 logger**

在 `api/v1/auth.py`, `api/v1/transcription.py` 等模块中引入 logger：

```python
import logging
logger = logging.getLogger(__name__)
```

在关键操作（登录、上传、转录）中添加 info/error 日志。

- [x] **Step 5: 将 `backend/logs/` 加入 `.gitignore`**

日志文件不应提交到版本控制：

```
backend/logs/
```

- [x] **Step 6: 启动后端验证日志输出**

```bash
cd backend
uvicorn app.main:app --reload
```

发送几个请求（登录、上传），检查：
- `backend/logs/app.log` 有请求日志
- `backend/logs/error.log` 为空（无错误时）

- [x] **Step 7: 更新计划文档状态**

标记 Task 16 各步骤完成。

- [x] **Step 8: 提交代码**

```bash
git add backend/app/logging_config.py backend/app/main.py backend/app/celery_app.py backend/app/api/v1/ backend/.gitignore
git commit -m "feat(task16): add logging config with rotation and component separation"
```

---
