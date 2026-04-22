# 在线音频转录网站 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于设计规格文档构建在线音频转录网站，支持用户注册登录、音频上传转录、说话人分离+时间戳、多格式下载、历史记录管理。

**Architecture:** FastAPI 后端提供 REST API，Celery Worker 异步处理转录任务，Vue3 SPA 前端采用 "The Sonic Gallery" 设计系统，PostgreSQL 存储，Redis 消息队列。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Celery, Redis, PostgreSQL, Vue3, Vite, Tailwind CSS, Pinia, mlx-audio/VibeVoice-ASR

---

## 阶段一：项目基础设施

### Task 1: 后端项目脚手架 — FastAPI + 目录结构 + 配置

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/requirements.txt`
- Create: `backend/.env`
- Create: `backend/.env.example`

- [ ] **Step 1: 创建后端目录结构**

```bash
mkdir -p backend/app/{api,models,services,tasks,schemas}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/tasks/__init__.py
touch backend/app/schemas/__init__.py
```

- [ ] **Step 2: 创建 requirements.txt**

```
# backend/requirements.txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy==2.0.40
alembic==1.15.2
asyncpg==0.30.0
psycopg2-binary==2.9.10
celery[redis]==5.5.2
redis==5.3.1
python-jose[cryptography]==3.4.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
pydantic==2.11.3
pydantic-settings==2.9.1
python-dotenv==1.1.0
httpx==0.28.1
pytest==8.3.5
pytest-asyncio==0.26.0
mlx-audio==0.3.0
```

- [ ] **Step 3: 创建配置模块 config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "STT Transcription API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://stt:stt123@localhost:5432/stt_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-this-to-a-secure-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_AUDIO_EXTENSIONS: set = {"wav", "mp3", "flac", "m4a", "ogg"}

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # MLX-Audio
    STT_MODEL: str = "mlx-community/VibeVoice-ASR-bf16"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: 创建 .env 和 .env.example**

```bash
# backend/.env.example
DATABASE_URL=postgresql+asyncpg://stt:stt123@localhost:5432/stt_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-this-to-a-secure-secret-in-production
UPLOAD_DIR=./uploads
```

```bash
# backend/.env — 复制 .env.example 内容，开发环境可直接用默认值
```

- [ ] **Step 5: 创建数据库连接模块**

```python
# backend/app/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 6: 创建 FastAPI 主入口 main.py**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
```

- [ ] **Step 7: 安装依赖并验证启动**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/api/health` 应返回 `{"status":"ok","app":"STT Transcription API"}`

- [ ] **Step 8: 写健康检查测试**

```python
# backend/tests/__init__.py
# 空文件
```

```python
# backend/tests/test_health.py
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
```

- [ ] **Step 9: 运行测试验证**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: 1 passed

- [ ] **Step 10: 提交**

```bash
git init  # 如果还没有 git 仓库
git add backend/ .gitignore
git commit -m "feat: initialize FastAPI backend scaffold with config and health check"
```

---

### Task 2: 数据库 — SQLAlchemy 模型 + Alembic 迁移

**Files:**
- Modify: `backend/app/database.py` — 添加枚举类型
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/transcription.py`
- Modify: `backend/app/models/__init__.py` — 导出所有模型
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/` (initial migration)

- [ ] **Step 1: 在 database.py 中定义转录状态枚举**

在 `database.py` 中添加 TranscriptionStatus 枚举，供模型和迁移共用：

```python
# backend/app/database.py — 新增内容
import enum

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class TranscriptionStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

- [ ] **Step 2: 创建 User 模型**

```python
# backend/app/models/user.py
import uuid

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)  # bcrypt hash
    real_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 3: 创建 Transcription 模型**

```python
# backend/app/models/transcription.py
import uuid

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, func, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TranscriptionStatus


class Transcription(Base):
    __tablename__ = "transcriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[TranscriptionStatus] = mapped_column(
        SAEnum(TranscriptionStatus, name="transcriptionstatus", create_constraint=True),
        default=TranscriptionStatus.pending,
        nullable=False,
        index=True,
    )
    model_used: Mapped[str] = mapped_column(String(200), nullable=False, default="mlx-community/VibeVoice-ASR-bf16")
    result_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", backref="transcriptions")
```

- [ ] **Step 4: 更新 models/__init__.py 导出所有模型**

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.transcription import Transcription

__all__ = ["User", "Transcription"]
```

- [ ] **Step 5: 初始化 Alembic**

在 `backend/` 目录下执行：

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz/backend
alembic init alembic
```

这会生成 `alembic.ini` 和 `alembic/` 目录。

- [ ] **Step 6: 配置 alembic.ini — 指向数据库 URL**

编辑 `alembic.ini`，将 `sqlalchemy.url` 改为从配置读取：

```ini
# 注释掉硬编码的 sqlalchemy.url
# sqlalchemy.url = driver://user:pass@localhost/dbname
sqlalchemy.url = postgresql+asyncpg://stt:stt123@localhost:5432/stt_db
```

> 注意：生产环境应从环境变量读取，开发阶段先用硬编码。

- [ ] **Step 7: 配置 alembic/env.py — 异步引擎 + 自动生成迁移**

替换 `alembic/env.py`，使其支持 asyncpg 和自动从 Base.metadata 生成迁移：

```python
# backend/alembic/env.py
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.database import Base
from app.models import User, Transcription  # noqa: F401 — 确保模型被导入
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 8: 生成初始迁移脚本**

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz/backend
alembic revision --autogenerate -m "create users and transcriptions tables"
```

检查生成的迁移文件，确认包含：
- `users` 表（id, email, password, real_name, department, phone, is_active, created_at）
- `transcriptions` 表（id, user_id FK, filename, file_path, file_size, duration, language, status enum, model_used, result_json, result_text, error_message, created_at, completed_at）
- `transcriptionstatus` 枚举类型
- 相应的索引（email unique, user_id index, status index）

- [ ] **Step 9: 提交**

```bash
git add backend/app/database.py backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat: add SQLAlchemy models (User, Transcription) and Alembic migration setup"
```

> 注意：此时 **不执行** `alembic upgrade head`，因为 PostgreSQL 还没启动（Task 3 会用 Docker Compose 启动）。迁移脚本的生成不需要数据库连接，但执行迁移需要。

---

### Task 3: Docker Compose — PostgreSQL + Redis

（待细化）

---

## 阶段二：后端核心功能

### Task 4: 用户认证 — 注册/登录/刷新/当前用户

（待细化）

---

### Task 5: 文件上传 — 接收音频 + 存储 + 创建记录

（待细化）

---

### Task 6: Celery 转录任务 — Worker + mlx-audio 调用

（待细化）

---

### Task 7: 转录结果 API — 列表/详情/状态查询

（待细化）

---

### Task 8: 下载功能 — 多格式生成 + zip 打包 + 原始音频

（待细化）

---

## 阶段三：前端基础

### Task 9: Vue3 脚手架 + 设计系统 + 路由 + 状态管理

（待细化）

---

### Task 10: API 客户端 + Auth 逻辑（登录/注册页）

（待细化）

---

## 阶段四：前端业务页面

### Task 11: 首页/转录页 — 上传区 + 进度条 + 布局框架

（待细化）

---

### Task 12: 历史记录页 — 表格 + 搜索筛选 + 分页

（待细化）

---

### Task 13: 转录详情页 — 说话人分色 + 时间戳 + 下载

（待细化）

---

### Task 14: 通用组件 — 侧边栏 + 顶栏 + 路由守卫

（待细化）

---

## 阶段五：集成与收尾

### Task 15: 前后端联调 + 健康检查 + 错误处理 + .gitignore

（待细化）
