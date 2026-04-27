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

**API 设计:**

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/transcriptions/` | 分页列表，支持 `?page=`、`?page_size=`、`?status=` 筛选 |
| `GET` | `/api/v1/transcriptions/{id}` | 详情查询，含完整 `result_json`、`result_text` |

**Schema 变更:**

新增 `TranscriptionDetailResponse`（继承 TranscriptionResponse，额外包含 `result_json`、`result_text`、`error_message`、`completed_at`）和 `TranscriptionListResponse`（分页包装：items, total, page, page_size, pages）。

**列表端点逻辑:**
1. 构建查询：`select(Transcription).where(user_id == current_user.id)`
2. 可选状态筛选
3. 按 `created_at.desc()` 排序
4. offset/limit 分页
5. 同时查询 count 计算总页数

**详情端点逻辑:**
1. 查询并鉴权（只能访问自己的记录）
2. 不存在返回 404

**权限控制:** 列表/详情均只能查询当前用户自己的转录任务。

- [x] **Step 1: 更新 Transcription schemas**
- [x] **Step 2: 添加列表和详情 API 端点**
- [x] **Step 3: 提交**

```bash
git commit -m "feat(task7): add transcription list and detail API endpoints"
```

---

### Task 8: 下载功能 — 多格式生成 + zip 打包 + 原始音频

**Goal:** 实现转录结果的多种格式下载，支持 JSON、TXT、SRT、VTT 字幕格式，以及 ZIP 打包（含所有格式 + 原始音频）。

**Files:**
- Create: `backend/app/services/export.py` — 格式转换核心服务
- Modify: `backend/app/api/v1/transcription.py` — 添加下载端点

**API 设计:**

```
GET /api/v1/transcriptions/{transcription_id}/download?format={format}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 是 | `json`, `txt`, `srt`, `vtt`, `zip` |

**响应:**
- `200 OK` — `Content-Disposition: attachment`，返回文件流
- `404` — 记录不存在
- `400` — 格式非法或转录尚未完成

**各格式内容规范:**

| 格式 | 文件名 | Content-Type |
|------|--------|--------------|
| `json` | `recording.json` | `application/json` |
| `txt` | `recording.txt` | `text/plain` |
| `srt` | `recording.srt` | `text/plain` |
| `vtt` | `recording.vtt` | `text/vtt` |
| `zip` | `recording.zip` | `application/zip` |

**export.py 核心函数:**

- `_seconds_to_srt_time(seconds)` → `00:01:23,450`
- `_seconds_to_vtt_time(seconds)` → `00:01:23.450`
- `generate_json(transcription)` — 格式化 JSON（含 segments + metadata）
- `generate_txt(transcription)` — 按说话人分段，含时间戳和完整文本
- `generate_srt(transcription)` — SubRip 字幕格式
- `generate_vtt(transcription)` — WebVTT 字幕格式
- `generate_zip(transcription)` — 内存中打包（`io.BytesIO` + `zipfile`）
- `export_transcription(transcription, format)` — 主分发函数，返回 `(mimetype, bytes)`

**下载端点逻辑:**
1. 查询并鉴权（同详情接口）
2. 校验状态必须为 `completed`
3. 校验 format 合法性
4. 调用 `export_transcription()` 生成内容
5. 返回 `StreamingResponse` + `Content-Disposition`

**边界处理:**

| 场景 | 处理 |
|------|------|
| 转录未完成 | 400 Bad Request |
| result_json 为空 | 400 Bad Request |
| format 非法 | 400 Bad Request，列出支持格式 |
| ZIP 中音频文件缺失 | 跳过音频，仅包含文本格式 |

- [x] **Step 1: 创建 export.py 格式转换服务**
- [x] **Step 2: 添加 download 端点到 transcription.py**
- [x] **Step 3: 提交**

```bash
git commit -m "feat(task8): add multi-format transcription download (json, txt, srt, vtt, zip)"
```

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
