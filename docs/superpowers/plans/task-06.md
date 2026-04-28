# Task 6: Celery 转录任务 — Worker + mlx-audio 调用

> 所属阶段: 阶段二：后端核心功能


**Goal:** 配置 Celery + Redis 任务队列，实现异步音频转录。上传文件后自动触发转录任务，Worker 调用 mlx-audio/VibeVoice-ASR 模型执行推理，并将结果（含说话人分离、时间戳）保存回数据库。

**关键设计决策:**
- Celery 是同步框架，因此需要独立的**同步 SQLAlchemy 会话**（`psycopg` 驱动），与主应用共用 `psycopg3` 驱动，仅需同步/异步引擎不同
- 模型在 **Worker 进程初始化时预加载**（`worker_process_init` 信号），避免每个任务重复加载带来的巨大开销
- 任务状态通过数据库 `Transcription.status` 字段流转（`pending` → `processing` → `completed`/`failed`），前端通过轮询详情接口获取进度
- 转录结果以结构化 JSON 保存到 `result_json`，纯文本保存到 `result_text`

**Files:**
- Create: `backend/app/database_sync.py` — 同步数据库引擎 + Session（供 Celery 使用）
- Create: `backend/app/celery_app.py` — Celery 应用配置
- Create: `backend/app/tasks/__init__.py` — tasks 包初始化
- Create: `backend/app/tasks/transcription.py` — 转录 Celery Task
- Modify: `backend/app/api/v1/transcription.py` — 上传后触发 Celery 任务
- Modify: `backend/.env.example` — 补充 Celery 配置示例（已有占位符，保持不变）
- Create: `backend/celery_worker.py` — Worker 启动入口（可选，也可用命令行）

---

- [x] **Step 1: 创建同步数据库会话 `database_sync.py`**

Celery Worker 运行在同步上下文中，无法直接使用 `create_async_engine`。创建一个独立的同步引擎，与主应用共用 `psycopg3` 驱动和同一套 URL：

```python
# backend/app/database_sync.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base

# psycopg3 同时支持同步和异步模式，URL 无需替换
SYNC_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SYNC_DATABASE_URL, echo=settings.DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

> **设计说明:**
> - 与 `database.py` 共用同一个 `Base` 和模型类，避免模型重复定义
> - 仅引擎和 sessionmaker 不同：同步引擎 + `SessionLocal()` 而非 `async_session()`
> - `psycopg3` 同时支持同步和异步，URL 无需替换，避免了在 `.env` 中维护两套连接字符串

---

- [x] **Step 2: 创建 Celery 应用配置 `celery_app.py`**

```python
# backend/app/celery_app.py
from celery import Celery
from app.config import settings

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
```

> **设计说明:**
> - `task_track_started=True` 让 Celery 记录任务从 `PENDING` 到 `STARTED` 的状态变化
> - `worker_prefetch_multiplier=1` 配合预加载的大模型，避免 worker 积压多个任务导致内存爆炸
> - `task_time_limit=3600` 为长音频（60 分钟）预留充足时间

---

- [x] **Step 3: 创建转录 Celery Task `tasks/transcription.py`**

```python
# backend/app/tasks/transcription.py
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
        # ── 1. 查询记录，状态设为 processing ──
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

        # ── 2. 调用 mlx-audio 执行转录 ──
        result = _stt_model.generate(
            audio=transcription.file_path,
            max_tokens=8192,
            temperature=0.0,
            verbose=False,
        )

        # ── 3. 保存结果到数据库 ──
        # result.text: 转录出的完整文本（可能包含 JSON 格式的说话人信息）
        # result.segments: 结构化段落列表，每个元素包含 start/end/speaker/text
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
        logger.info("Transcription %s completed in %.2fs", transcription_id, result.total_time)

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
```

同时创建 `tasks/__init__.py`（空文件或导出 task）：

```python
# backend/app/tasks/__init__.py
from app.tasks.transcription import transcribe_audio

__all__ = ["transcribe_audio"]
```

> **设计说明:**
> - `worker_process_init` 而非 `worker_init`：Celery prefork pool 下，前者在每个子进程 fork **后** 触发，后者只在主进程触发一次。模型必须在每个子进程中独立加载（MLX/Metal 上下文不可跨进程共享）
> - `bind=True` 让 task 接收 `self`，可通过 `self.update_state()` 更新 Celery 内部状态
> - `transcription_id` 使用字符串而非 UUID 对象，因为 Celery JSON serializer 无法序列化 UUID
> - `max_retries=2, default_retry_delay=60`：偶发性错误（如文件锁、短暂内存不足）自动重试
> - `result_json` 保存完整的结构化数据（segments、token 统计、耗时），`result_text` 保存纯文本供前端直接展示

---

- [x] **Step 4: 修改上传接口，上传成功后触发 Celery 任务**

在 `backend/app/api/v1/transcription.py` 的 `create_transcription` 函数末尾，数据库提交后添加任务触发：

```python
# backend/app/api/v1/transcription.py — 新增导入
from app.tasks.transcription import transcribe_audio

# ... 在 create_transcription 函数中，await db.refresh(transcription) 之后添加：
    # 触发异步转录任务
    transcribe_audio.delay(str(transcription.id))

    return transcription
```

> **设计说明:**
> - `.delay()` 是 Celery 的异步投递方法，立即返回不阻塞 HTTP 响应
> - `str(transcription.id)` 将 UUID 转为字符串，满足 JSON 序列化要求
> - 前端收到 201 Created 响应时，转录已在后台启动，可通过轮询详情接口跟踪状态

---

- [x] **Step 5: 创建 Worker 启动入口 `celery_worker.py`**

```python
# backend/celery_worker.py
"""Celery Worker 启动入口。

开发环境启动命令:
    python celery_worker.py

或使用 Celery CLI:
    celery -A app.celery_app worker --loglevel=info -c 1

-c 1 表示单并发，推荐 Apple Silicon 开发环境使用，避免多个进程同时加载大模型耗尽内存。
"""
from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()
```

> **设计说明:**
> - 提供 `python celery_worker.py` 作为简便启动方式
> - 生产环境或需要多并发时，使用 `celery -A app.celery_app worker --loglevel=info -c ${CONCURRENCY}`
> - **Apple Silicon 建议 `-c 1`**：VibeVoice-ASR-bf16 模型约 3GB，多并发加载多个实例可能耗尽统一内存

---

- [x] **Step 6: 验证流程（手动测试步骤）**

启动顺序（需要三个终端窗口）：

```bash
# 终端 1: 启动 Redis（已在本地运行）
redis-server

# 终端 2: 启动 Celery Worker
cd /Users/qizhao/project_git/stt_qzqzqqz/backend
source /Users/qizhao/.venvs/mlx-audio/bin/activate
celery -A app.celery_app worker --loglevel=info -c 1

# 终端 3: 启动 FastAPI 服务
source /Users/qizhao/.venvs/mlx-audio/bin/activate
uvicorn app.main:app --reload --port 8000
```

测试步骤：
1. 登录获取 JWT Token
2. `POST /api/v1/transcriptions/` 上传音频文件
3. 观察 Worker 终端输出：模型加载 → 转录开始 → 完成
4. `GET /api/v1/transcriptions/{id}` 查看状态变化和 `result_json` / `result_text`

---

- [x] **Step 7: 提交**

```bash
git add backend/app/database_sync.py backend/app/celery_app.py \
    backend/app/tasks/ backend/app/api/v1/transcription.py \
    backend/celery_worker.py
git commit -m "feat: add Celery transcription worker with mlx-audio integration"
```

---
