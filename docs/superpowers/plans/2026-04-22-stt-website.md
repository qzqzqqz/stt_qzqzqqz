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

（待细化）

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
