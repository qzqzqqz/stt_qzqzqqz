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

- [x] **Step 1: 创建后端目录结构**

```bash
mkdir -p backend/app/{api,models,services,tasks,schemas}
touch backend/app/__init__.py
touch backend/app/api/__init__.py
touch backend/app/models/__init__.py
touch backend/app/services/__init__.py
touch backend/app/tasks/__init__.py
touch backend/app/schemas/__init__.py
```

- [x] **Step 2: 创建 requirements.txt**

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

- [x] **Step 3: 创建配置模块 config.py**

```python
# backend/app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "STT Transcription API"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+psycopg://stt:stt123@localhost:5432/stt_db"

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

- [x] **Step 4: 创建 .env 和 .env.example**

```bash
# backend/.env.example
DATABASE_URL=postgresql+psycopg://stt:stt123@localhost:5432/stt_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-this-to-a-secure-secret-in-production
UPLOAD_DIR=./uploads
```

```bash
# backend/.env — 复制 .env.example 内容，开发环境可直接用默认值
```

- [x] **Step 5: 创建数据库连接模块**

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

- [x] **Step 6: 创建 FastAPI 主入口 main.py**

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

- [x] **Step 7: 安装依赖并验证启动**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

访问 `http://localhost:8000/api/health` 应返回 `{"status":"ok","app":"STT Transcription API"}`

- [x] **Step 8: 写健康检查测试**

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

- [x] **Step 9: 运行测试验证**

```bash
cd backend
pytest tests/test_health.py -v
```

Expected: 1 passed

- [x] **Step 10: 提交**

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

- [x] **Step 1: 在 database.py 中定义转录状态枚举**

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

- [x] **Step 2: 创建 User 模型**

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

- [x] **Step 3: 创建 Transcription 模型**

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

- [x] **Step 4: 更新 models/__init__.py 导出所有模型**

```python
# backend/app/models/__init__.py
from app.models.user import User
from app.models.transcription import Transcription

__all__ = ["User", "Transcription"]
```

- [x] **Step 5: 初始化 Alembic**

在 `backend/` 目录下执行：

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz/backend
alembic init alembic
```

这会生成 `alembic.ini` 和 `alembic/` 目录。

- [x] **Step 6: 配置 alembic.ini — 指向数据库 URL**

编辑 `alembic.ini`，将 `sqlalchemy.url` 改为从配置读取：

```ini
# 注释掉硬编码的 sqlalchemy.url
# sqlalchemy.url = driver://user:pass@localhost/dbname
sqlalchemy.url = postgresql+psycopg://stt:stt123@localhost:5432/stt_db
```

> 注意：生产环境应从环境变量读取，开发阶段先用硬编码。

- [x] **Step 7: 配置 alembic/env.py — 异步引擎 + 自动生成迁移**

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

**Goal:** 提供标准化的容器化开发环境，新协作者可一键启动所有依赖服务。端口映射避开现有本地服务（PostgreSQL 5432 → 5433，Redis 6379 → 6380），本地开发不受影响。

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/.dockerignore`
- Create: `backend/Dockerfile`
- Create: `.env.docker`

- [x] **Step 1: 创建 docker-compose.yml**

提供 PostgreSQL + Redis 两个服务，使用非冲突端口：

```yaml
# docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:16-alpine
    container_name: stt-postgres
    ports:
      - "5433:5432"
    environment:
      POSTGRES_USER: qzqzqqz
      POSTGRES_PASSWORD: ""
      POSTGRES_DB: stt_qzqzqqz
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U qzqzqqz -d stt_qzqzqqz"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: stt-redis
    ports:
      - "6380:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

- [ ] **Step 2: 创建 backend/.dockerignore**

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
.venv
venv/
env/
.env
.env.local
*.egg-info/
dist/
build/
uploads/
alembic/versions/*.py
!alembic/versions/.gitkeep
```

- [ ] **Step 3: 创建 backend/Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [x] **Step 4: 创建 .env.docker**

```bash
# .env.docker — Docker 环境专用配置
# 使用服务名作为主机名（docker-compose 内部网络解析）
DATABASE_URL=postgresql+psycopg://qzqzqqz@postgres:5432/stt_qzqzqqz
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-this-to-a-secure-secret-in-production
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
UPLOAD_DIR=./uploads
```

- [x] **Step 5: 验证 Docker Compose 启动**

文件已创建，验证待 Docker Desktop 启动后手动执行：

```bash
# 启动服务
docker-compose up -d

# 检查状态
docker-compose ps

# 测试 PostgreSQL 连接（通过映射端口 5433）
psql postgresql://qzqzqqz@localhost:5433/stt_qzqzqqz

# 测试 Redis 连接（通过映射端口 6380）
redis-cli -p 6380 ping
```

> **说明：** 本地开发继续使用现有的本地 PostgreSQL（5432）和 Redis（6379）。Docker Compose 是可选的标准化方案，不影响现有开发流程。后续需要 Docker 环境时再启动验证。

---

## 阶段二：后端核心功能

### Task 4: 用户认证 — 注册/登录/刷新/当前用户

**Goal:** 实现基于 JWT 的用户认证系统，支持注册、登录、Token 刷新和获取当前用户。密码使用 bcrypt 哈希，JWT 使用 python-jose 处理。

**依赖:** `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`（已存在于 requirements.txt）

**Files:**
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/core/security.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/v1/__init__.py`
- Create: `backend/app/api/v1/auth.py`
- Modify: `backend/app/main.py` — 注册 auth 路由

- [x] **Step 1: 创建 Pydantic Schemas**

```python
# backend/app/schemas/user.py
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict


class UserBase(BaseModel):
    email: EmailStr
    real_name: str
    department: str
    phone: str | None = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

- [x] **Step 2: 创建安全工具 — JWT + bcrypt**

```python
# backend/app/core/security.py
from datetime import datetime, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": subject, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"exp": expire, "sub": subject, "type": "refresh"}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
```

- [x] **Step 3: 创建依赖注入 — get_current_user**

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return user
```

- [x] **Step 4: 创建认证路由**

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=user_in.email,
        password=get_password_hash(user_in.password),
        real_name=user_in.real_name,
        department=user_in.department,
        phone=user_in.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=Token)
async def refresh(token: str, db: AsyncSession = Depends(get_db)):
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
```

- [x] **Step 5: 创建 v1 路由聚合并注册到 main.py**

```python
# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
```

```python
# backend/app/main.py — 新增
from fastapi import FastAPI
from app.api.v1 import api_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router)
```

> **设计说明:**
> - 登录接口使用 `OAuth2PasswordRequestForm`，Swagger UI 会自动渲染登录表单
> - `username` 字段接收 email（OAuth2 标准字段名）
> - Token payload 包含 `type` 字段区分 access/refresh，防止 refresh token 被误用于访问
> - `get_current_user` 依赖注入到需要认证的路由上，自动完成 JWT 验证

---

### Task 5: 文件上传 — 接收音频 + 存储 + 创建记录

**Goal:** 实现音频文件上传接口，验证格式与大小，保存到本地目录，并在数据库中创建对应的 Transcription 记录。

**Files:**
- Create: `backend/app/schemas/transcription.py`
- Create: `backend/app/services/upload.py`
- Create: `backend/app/api/v1/transcription.py`
- Modify: `backend/app/api/v1/__init__.py` — 注册转录路由
- Modify: `backend/app/main.py` — 确保上传目录存在

- [x] **Step 1: 创建 Transcription Schemas**

```python
# backend/app/schemas/transcription.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.database import TranscriptionStatus


class TranscriptionBase(BaseModel):
    filename: str
    language: str | None = None


class TranscriptionCreate(TranscriptionBase):
    pass


class TranscriptionResponse(TranscriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_size: int
    duration: float | None = None
    status: TranscriptionStatus
    model_used: str
    created_at: datetime
```

- [x] **Step 2: 创建文件上传服务**

```python
# backend/app/services/upload.py
import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = settings.ALLOWED_AUDIO_EXTENSIONS
MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def validate_file(file: UploadFile) -> None:
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format: .{ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 大小校验在读取后执行（UploadFile 不预读大小）


async def save_upload_file(file: UploadFile, user_id: str) -> tuple[str, int]:
    """保存上传文件，返回 (文件路径, 文件大小)."""
    validate_file(file)

    ext = _get_extension(file.filename or "")
    file_name = f"{uuid.uuid4()}.{ext}"
    user_dir = Path(settings.UPLOAD_DIR) / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    file_path = user_dir / file_name

    size = 0
    with open(file_path, "wb") as buffer:
        while chunk := await file.read(8192):
            size += len(chunk)
            if size > MAX_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max size: {settings.MAX_UPLOAD_SIZE_MB} MB",
                )
            buffer.write(chunk)

    return str(file_path), size
```

- [x] **Step 3: 创建转录上传路由**

```python
# backend/app/api/v1/transcription.py
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.models.user import User
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionResponse
from app.services.upload import save_upload_file

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(
    file: UploadFile = File(...),
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传音频文件并创建转录任务."""
    file_path, file_size = await save_upload_file(file, str(current_user.id))

    transcription = Transcription(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=file_size,
        language=language,
        status=TranscriptionStatus.pending,
        model_used=settings.STT_MODEL,
    )
    db.add(transcription)
    await db.commit()
    await db.refresh(transcription)
    return transcription
```

- [x] **Step 4: 注册转录路由到 v1 聚合器**

```python
# backend/app/api/v1/__init__.py
from fastapi import APIRouter

from app.api.v1 import auth, transcription

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(transcription.router)
```

- [x] **Step 5: 确保上传目录在应用启动时存在**

```python
# backend/app/main.py — 在 app 创建后添加
from pathlib import Path
from app.config import settings

Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
```

> **设计说明:**
> - 文件按用户 ID 分目录存储：`uploads/{user_id}/{uuid}.{ext}`，避免文件名冲突
> - 流式读取 + 边读边校验大小，避免大文件占用过多内存
> - 仅保存原始文件名到数据库，实际存储使用 UUID 命名，防止路径遍历攻击
> - 创建记录时状态为 `pending`，等待 Celery Worker 处理转录

---

### Task 6: Celery 转录任务 — Worker + mlx-audio 调用

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

### Task 7: 转录结果 API — 列表/详情/状态查询

**Goal:** 实现转录任务的列表查询（分页）、详情查询和状态查询接口。

**Files:**
- Modify: `backend/app/schemas/transcription.py` — 新增详情/列表响应 Schema
- Modify: `backend/app/api/v1/transcription.py` — 新增列表和详情端点

- [x] **Step 1: 更新 Transcription schemas**

新增 `TranscriptionDetailResponse`（详情视图，含完整结果数据）和 `TranscriptionListResponse`（分页包装）：

```python
# backend/app/schemas/transcription.py
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.database import TranscriptionStatus


class TranscriptionBase(BaseModel):
    filename: str
    language: str | None = None


class TranscriptionCreate(TranscriptionBase):
    pass


class TranscriptionResponse(TranscriptionBase):
    """列表视图响应 — 不包含完整结果数据."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    file_size: int
    duration: float | None = None
    status: TranscriptionStatus
    model_used: str
    created_at: datetime


class TranscriptionDetailResponse(TranscriptionResponse):
    """详情视图响应 — 包含完整转录结果."""

    result_json: dict | None = None
    result_text: str | None = None
    error_message: str | None = None
    completed_at: datetime | None = None


class TranscriptionListResponse(BaseModel):
    """分页列表响应."""

    items: list[TranscriptionResponse]
    total: int
    page: int
    page_size: int
    pages: int
```

- [x] **Step 2: 添加列表和详情 API 端点**

```python
# backend/app/api/v1/transcription.py
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.api.deps import get_current_user, get_db
from app.config import settings
from app.database import TranscriptionStatus
from app.models.transcription import Transcription
from app.models.user import User
from app.schemas.transcription import (
    TranscriptionDetailResponse,
    TranscriptionListResponse,
    TranscriptionResponse,
)
from app.services.export import export_transcription
from app.services.upload import save_upload_file
from app.tasks.transcription import transcribe_audio

router = APIRouter(prefix="/transcriptions", tags=["transcriptions"])


@router.post("/", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_transcription(...):
    """上传音频文件并创建转录任务."""
    ...


@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: TranscriptionStatus | None = Query(None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询当前用户的转录任务列表（分页）."""
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    count_query = select(func.count()).select_from(Transcription).where(Transcription.user_id == current_user.id)

    if status:
        query = query.where(Transcription.status == status)
        count_query = count_query.where(Transcription.status == status)

    query = query.order_by(Transcription.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    pages = (total + page_size - 1) // page_size

    return TranscriptionListResponse(
        items=list(items), total=total, page=page, page_size=page_size, pages=pages,
    )


@router.get("/{transcription_id}", response_model=TranscriptionDetailResponse)
async def get_transcription(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询单个转录任务详情."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    return transcription
```

> **设计说明:**
> - 列表端点仅返回基础字段，不含 `result_json`/`result_text`，避免大字段拖慢列表加载
> - 详情端点返回完整数据，供前端展示转录结果和下载
> - 分页参数限制 `page_size` 最大 100，防止恶意大分页
> - 两个端点均通过 `user_id == current_user.id` 鉴权，只能访问自己的记录

- [x] **Step 3: 提交**

```bash
git add app/api/v1/transcription.py app/schemas/transcription.py
git commit -m "feat(task7): add transcription list and detail API endpoints"
```

---

### Task 8: 下载功能 — 多格式生成 + zip 打包 + 原始音频

**Goal:** 实现转录结果的多种格式下载，支持 JSON、TXT、SRT、VTT 字幕格式，以及 ZIP 打包（含所有格式 + 原始音频）。

**Files:**
- Create: `backend/app/services/export.py` — 格式转换核心服务
- Modify: `backend/app/api/v1/transcription.py` — 添加下载端点

- [x] **Step 1: 创建 export.py 格式转换服务**

```python
# backend/app/services/export.py
"""转录结果导出服务 — 支持 JSON、TXT、SRT、VTT、ZIP 多种格式."""

import io
import json
import zipfile
from datetime import timedelta

from app.models.transcription import Transcription


def _seconds_to_srt_time(seconds: float) -> str:
    """秒数转 SRT 时间格式 HH:MM:SS,mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _seconds_to_vtt_time(seconds: float) -> str:
    """秒数转 VTT 时间格式 HH:MM:SS.mmm."""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def generate_json(transcription: Transcription) -> bytes:
    data = {
        "filename": transcription.filename,
        "model": transcription.model_used,
        "language": transcription.language,
        "duration": transcription.duration,
        "segments": transcription.result_json.get("segments", []) if transcription.result_json else [],
        "metadata": {k: v for k, v in (transcription.result_json or {}).items() if k != "segments"},
    }
    return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")


def generate_txt(transcription: Transcription) -> bytes:
    lines = []
    lines.append("=" * 80)
    lines.append(f"音频文件: {transcription.filename}")
    lines.append(f"转录模型: {transcription.model_used}")
    lines.append(f"语言: {transcription.language or '未知'}")
    lines.append("=" * 80)
    lines.append("")

    for seg in _get_segments(transcription):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        lines.append(f"[{start} - {end}] {seg['speaker']}:")
        lines.append(seg["text"])
        lines.append("")

    lines.append("=" * 80)
    lines.append("完整文本:")
    lines.append("=" * 80)
    lines.append(transcription.result_text or "")
    return "\n".join(lines).encode("utf-8")


def generate_srt(transcription: Transcription) -> bytes:
    segments = _get_segments(transcription)
    lines = []
    for idx, seg in enumerate(segments, start=1):
        start = _seconds_to_srt_time(seg["start"])
        end = _seconds_to_srt_time(seg["end"])
        lines.append(str(idx))
        lines.append(f"{start} --> {end}")
        lines.append(f"{seg['speaker']}: {seg['text']}")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def generate_vtt(transcription: Transcription) -> bytes:
    segments = _get_segments(transcription)
    lines = [f"WEBVTT - {transcription.filename}", ""]
    for seg in segments:
        start = _seconds_to_vtt_time(seg["start"])
        end = _seconds_to_vtt_time(seg["end"])
        lines.append(f"{start} --> {end}")
        lines.append(f"<v {seg['speaker']}>{seg['text']}</v>")
        lines.append("")
    return "\n".join(lines).encode("utf-8")


def generate_zip(transcription: Transcription) -> bytes:
    buffer = io.BytesIO()
    base_name = transcription.filename.rsplit(".", 1)[0]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{base_name}.json", generate_json(transcription))
        zf.writestr(f"{base_name}.txt", generate_txt(transcription))
        zf.writestr(f"{base_name}.srt", generate_srt(transcription))
        zf.writestr(f"{base_name}.vtt", generate_vtt(transcription))
        import os
        if os.path.exists(transcription.file_path):
            zf.write(transcription.file_path, arcname=transcription.filename)
    return buffer.getvalue()


def _get_segments(transcription: Transcription) -> list[dict]:
    if not transcription.result_json:
        return []
    return [
        {
            "start": seg.get("start_time", 0.0),
            "end": seg.get("end_time", 0.0),
            "speaker": f"Speaker {seg.get('speaker_id', 'Unknown')}",
            "text": seg.get("text", "").strip(),
        }
        for seg in transcription.result_json.get("segments", [])
    ]


_FORMAT_MAP = {
    "json": ("application/json", generate_json),
    "txt": ("text/plain; charset=utf-8", generate_txt),
    "srt": ("text/plain; charset=utf-8", generate_srt),
    "vtt": ("text/vtt; charset=utf-8", generate_vtt),
    "zip": ("application/zip", generate_zip),
}


def export_transcription(transcription: Transcription, format: str) -> tuple[str, bytes]:
    fmt = format.lower()
    if fmt not in _FORMAT_MAP:
        raise ValueError(f"不支持的格式: {format}。支持: {', '.join(_FORMAT_MAP.keys())}")
    if not transcription.result_json and fmt != "zip":
        raise ValueError("转录结果数据不可用")
    mimetype, generator = _FORMAT_MAP[fmt]
    return mimetype, generator(transcription)
```

> **设计说明:**
> - ZIP 使用 `io.BytesIO` 在内存中构建，不落磁盘临时文件
> - SRT 时间格式 `HH:MM:SS,mmm`，VTT 时间格式 `HH:MM:SS.mmm`（毫秒分隔符差异）
> - 所有生成函数接收 `Transcription` ORM 对象，统一从 `result_json` 提取 segments

- [x] **Step 2: 添加 download 端点到 transcription.py**

```python
# backend/app/api/v1/transcription.py
import io
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

# ... 已有导入
from app.services.export import export_transcription


@router.get("/{transcription_id}/download")
async def download_transcription(
    transcription_id: uuid.UUID,
    format: str = Query(..., description="导出格式: json, txt, srt, vtt, zip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载转录结果（多种格式）."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if transcription.status != TranscriptionStatus.completed:
        raise HTTPException(
            status_code=400,
            detail=f"Transcription not completed (current status: {transcription.status.value})",
        )

    try:
        mimetype, content = export_transcription(transcription, format)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    base_name = os.path.splitext(transcription.filename)[0]
    download_filename = f"{base_name}.{format.lower()}"

    return StreamingResponse(
        io.BytesIO(content),
        media_type=mimetype,
        headers={"Content-Disposition": f'attachment; filename="{download_filename}"'},
    )
```

> **设计说明:**
> - 端点返回 `StreamingResponse`，流式传输避免大文件占用过多内存
> - 仅 `completed` 状态可下载，防止下载不完整结果
> - `Content-Disposition: attachment` 强制浏览器下载而非预览
> - ZIP 中原始音频文件不存在时自动跳过，不影响文本格式打包

- [x] **Step 3: 提交**

```bash
git add app/services/export.py app/api/v1/transcription.py
git commit -m "feat(task8): add multi-format transcription download (json, txt, srt, vtt, zip)"
```

---

## 阶段三：前端基础

### Task 9: Vue3 脚手架 + 设计系统 + 路由 + 状态管理

**Goal:** 从零搭建 Vue3 SPA 前端项目，集成 Vite + TypeScript + Tailwind CSS + Vue Router + Pinia，配置 "The Sonic Gallery" 设计系统，建立基础目录结构和布局框架。

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`, `tsconfig.app.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/assets/main.css`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/auth.ts`, `stores/app.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/AppLayout.vue`, `AppSidebar.vue`, `AppTopbar.vue`
- Create: `frontend/src/views/LoginView.vue`, `RegisterView.vue`, `DashboardView.vue`, `HistoryView.vue`, `TranscriptionDetailView.vue`

- [ ] **Step 1: 初始化 Vue3 + Vite 项目**

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz
npm create vite@latest frontend -- --template vue-ts
```

选择 Vue + TypeScript，这会生成 `frontend/` 目录和基础文件结构。

- [ ] **Step 2: 安装依赖**

```bash
cd frontend
npm install
npm install vue-router@4 pinia axios
npm install -D tailwindcss @tailwindcss/vite
```

- [ ] **Step 3: 配置 Tailwind CSS（The Sonic Gallery 设计系统）**

创建 `frontend/tailwind.config.ts`：

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0053db',
        'primary-dim': '#0048c1',
        surface: '#f7f9fb',
        'surface-container-low': '#f0f4f7',
        'surface-container': '#e8eff3',
        'surface-container-high': '#d9e4ea',
        'surface-container-highest': '#d9e4ea',
        'on-surface': '#2a3439',
        'on-surface-variant': '#566166',
        'outline-variant': '#a9b4b9',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 12px 40px rgba(42, 52, 57, 0.06)',
      },
      borderRadius: {
        md: '0.75rem',
      },
    },
  },
  plugins: [],
} satisfies Config
```

创建 `frontend/src/assets/main.css`：

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import 'tailwindcss';

@theme {
  --color-primary: #0053db;
  --color-primary-dim: #0048c1;
  --color-surface: #f7f9fb;
  --color-surface-container-low: #f0f4f7;
  --color-surface-container: #e8eff3;
  --color-surface-container-high: #d9e4ea;
  --color-surface-container-highest: #d9e4ea;
  --color-on-surface: #2a3439;
  --color-on-surface-variant: #566166;
  --color-outline-variant: #a9b4b9;
  --font-sans: 'Inter', system-ui, sans-serif;
}

body {
  @apply bg-surface text-on-surface font-sans antialiased;
}
```

> **设计说明:**
> - 颜色系统遵循 "The Sonic Gallery" 规范：信号蓝 `#0053db` 为主色，表面灰 `#f7f9fb` 为背景
> - 无边框原则：用背景色差分层，禁用 1px solid 边框做区域划分
> - 环境阴影使用 `rgba(42,52,57,0.06)`，不用纯黑

- [ ] **Step 4: 配置 Vite 和路径别名**

更新 `frontend/vite.config.ts`：

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

更新 `frontend/tsconfig.app.json` 添加路径别名：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

> **设计说明:**
> - Vite dev server 代理 `/api` 到后端 `localhost:8000`，开发环境直接联调
> - 路径别名 `@/` 指向 `src/`，避免相对路径 `../../../` 地狱

- [ ] **Step 5: 配置 Vue Router + 路由守卫**

创建 `frontend/src/router/index.ts`：

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/HistoryView.vue'),
        },
        {
          path: 'transcriptions/:id',
          name: 'transcription-detail',
          component: () => import('@/views/TranscriptionDetailView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem('access_token')
  if (!to.meta.public && !isAuthenticated) {
    next({ name: 'login' })
  } else {
    next()
  }
})

export default router
```

> **设计说明:**
> - 登录/注册页标记 `meta: { public: true }`，路由守卫放行
> - 未登录用户访问受保护路由自动跳转 `/login`
> - 布局路由使用 `AppLayout.vue` 作为父级，子路由嵌套在内容区

- [ ] **Step 6: 配置 Pinia 状态管理**

创建 `frontend/src/stores/auth.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: string
  email: string
  real_name: string
  department: string
  phone: string | null
  is_active: boolean
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearAuth() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function setUser(userData: User) {
    user.value = userData
  }

  return {
    accessToken, refreshToken, user,
    isAuthenticated, setTokens, clearAuth, setUser,
  }
})
```

创建 `frontend/src/stores/app.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const isLoading = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarCollapsed, isLoading, toggleSidebar }
})
```

- [ ] **Step 7: 创建 API 客户端**

创建 `frontend/src/api/client.ts`：

```typescript
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

> **设计说明:**
> - 请求拦截器自动附加 JWT token，无需每个 API 调用手动传 token
> - 响应拦截器统一处理 401：清除 token 并跳转登录页

- [ ] **Step 8: 创建布局组件**

创建 `frontend/src/components/AppLayout.vue`：

```vue
<template>
  <div class="flex h-screen bg-surface">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <AppTopbar />
      <main class="flex-1 overflow-auto p-6">
        <div class="max-w-7xl mx-auto">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
</script>
```

创建 `frontend/src/components/AppSidebar.vue`：

```vue
<template>
  <aside class="w-64 h-screen fixed left-0 top-0 z-50 flex flex-col">
    <div class="h-full bg-surface/80 backdrop-blur-xl border-r border-outline-variant/20 flex flex-col">
      <div class="h-16 flex items-center px-6">
        <span class="text-xl font-semibold text-primary">STT</span>
      </div>
      <nav class="flex-1 px-4 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors"
          :class="route.path === item.path ? 'bg-primary text-white' : 'text-on-surface-variant hover:bg-surface-container-low'"
        >
          <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="p-4 border-t border-outline-variant/20">
        <button
          @click="logout"
          class="flex items-center gap-3 px-4 py-3 w-full rounded-md text-sm text-on-surface-variant hover:bg-surface-container-low transition-colors"
        >
          <span class="material-symbols-outlined text-lg">logout</span>
          退出登录
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { path: '/', label: '仪表盘', icon: 'dashboard' },
  { path: '/history', label: '历史记录', icon: 'history' },
]

function logout() {
  authStore.clearAuth()
  router.push({ name: 'login' })
}
</script>
```

创建 `frontend/src/components/AppTopbar.vue`：

```vue
<template>
  <header class="h-16 bg-surface/80 backdrop-blur-xl border-b border-outline-variant/20 flex items-center justify-between px-6 sticky top-0 z-40">
    <h1 class="text-headline-sm font-semibold tracking-tight">{{ pageTitle }}</h1>
    <div class="flex items-center gap-4">
      <span class="text-sm text-on-surface-variant">{{ authStore.user?.real_name }}</span>
      <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-medium">
        {{ authStore.user?.real_name?.[0] || '?' }}
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    dashboard: '转录工作台',
    history: '历史记录',
    'transcription-detail': '转录详情',
  }
  return titles[route.name as string] || ''
})
</script>
```

> **设计说明:**
> - 侧边栏和顶部栏均使用毛玻璃效果 `backdrop-blur-xl` + 半透明背景
> - 左侧栏固定宽 64，主内容区 `max-w-7xl` 居中，适配大屏
> - 导航当前项使用主色背景，非当前项 hover 显示 `surface-container-low`

- [ ] **Step 9: 创建页面占位组件**

创建 5 个空壳页面（后续 Task 10-13 填充内容）：

```vue
<!-- frontend/src/views/LoginView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <h2 class="text-headline-sm font-semibold">登录</h2>
    <p class="text-on-surface-variant mt-2">开发中...</p>
  </div>
</template>
```

同理创建 `RegisterView.vue`、`DashboardView.vue`、`HistoryView.vue`、`TranscriptionDetailView.vue`。

- [ ] **Step 10: 配置应用入口**

更新 `frontend/src/main.ts`：

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

更新 `frontend/src/App.vue`：

```vue
<template>
  <RouterView />
</template>
```

更新 `frontend/index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
    <title>STT 音频转录</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 11: 验证启动**

```bash
cd frontend
npm run dev
```

验证：
- `http://localhost:5173/login` 显示登录页占位
- `http://localhost:5173/` 因未登录自动跳转 `/login`
- localStorage 中手动设置 `access_token=test` 后刷新 `/` 显示布局框架

- [ ] **Step 12: 提交**

```bash
git add frontend/
git commit -m "feat(task9): scaffold Vue3 frontend with Vite, Tailwind, Router, Pinia"
```

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
