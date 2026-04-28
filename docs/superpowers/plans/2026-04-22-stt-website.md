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

- [x] **Step 1: 初始化 Vue3 + Vite 项目**

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz
npm create vite@latest frontend -- --template vue-ts
```

选择 Vue + TypeScript，这会生成 `frontend/` 目录和基础文件结构。

- [x] **Step 2: 安装依赖**

```bash
cd frontend
npm install
npm install vue-router@4 pinia axios
npm install -D tailwindcss @tailwindcss/vite
```

- [x] **Step 3: 配置 Tailwind CSS（The Sonic Gallery 设计系统）**

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

- [x] **Step 4: 配置 Vite 和路径别名**

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

- [x] **Step 5: 配置 Vue Router + 路由守卫**

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

- [x] **Step 6: 配置 Pinia 状态管理**

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

- [x] **Step 7: 创建 API 客户端**

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

- [x] **Step 8: 创建布局组件**

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

- [x] **Step 9: 创建页面占位组件**

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

- [x] **Step 10: 配置应用入口**

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

- [x] **Step 11: 验证启动**

```bash
cd frontend
npm run dev
```

验证：
- `http://localhost:5173/login` 显示登录页占位
- `http://localhost:5173/` 因未登录自动跳转 `/login`
- localStorage 中手动设置 `access_token=test` 后刷新 `/` 显示布局框架

- [x] **Step 12: 提交**

```bash
git add frontend/
git commit -m "feat(task9): scaffold Vue3 frontend with Vite, Tailwind, Router, Pinia"
```

---

### Task 10: API 客户端 + Auth 逻辑（登录/注册页）

**Goal:** 实现前端认证 API 模块，完成登录/注册页面，与后端 JWT 认证系统对接。

**Files:**
- Create: `frontend/src/api/auth.ts` — 认证相关 API 封装
- Modify: `frontend/src/stores/auth.ts` — 添加 login/register/fetchUser actions
- Modify: `frontend/src/views/LoginView.vue` — 登录表单页面
- Modify: `frontend/src/views/RegisterView.vue` — 注册表单页面
- Modify: `frontend/src/router/index.ts` — 登录后获取用户信息

- [x] **Step 1: 创建认证 API 模块**

```typescript
// frontend/src/api/auth.ts
import client from './client'

export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  password: string
  real_name: string
  department: string
  phone?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  real_name: string
  department: string
  phone: string | null
  is_active: boolean
  created_at: string
}

export async function login(form: LoginForm): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', form.email)
  params.append('password', form.password)
  const { data } = await client.post('/v1/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function register(form: RegisterForm): Promise<User> {
  const { data } = await client.post('/v1/auth/register', form)
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await client.get('/v1/auth/me')
  return data
}
```

> **设计说明:**
> - 登录接口使用 `application/x-www-form-urlencoded`，因为后端使用 `OAuth2PasswordRequestForm`
> - 注册接口使用 JSON，与后端 `UserCreate` schema 对应
> - API 层只做 HTTP 调用，不处理状态管理（状态由 Pinia store 处理）

- [x] **Step 2: 更新 auth store**

在 `frontend/src/stores/auth.ts` 中添加异步 actions：

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, fetchCurrentUser } from '@/api/auth'
import type { LoginForm, RegisterForm, User } from '@/api/auth'

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

  async function login(form: LoginForm) {
    const data = await loginApi(form)
    setTokens(data.access_token, data.refresh_token)
    const userData = await fetchCurrentUser()
    user.value = userData
  }

  async function register(form: RegisterForm) {
    await registerApi(form)
  }

  async function fetchUser() {
    if (!accessToken.value) return
    const userData = await fetchCurrentUser()
    user.value = userData
  }

  return {
    accessToken, refreshToken, user,
    isAuthenticated, login, register, fetchUser, clearAuth,
  }
})
```

> **设计说明:**
> - `login()` 先获取 token，再调用 `/me` 获取用户信息，确保登录后 store 中 user 立即可用
> - `fetchUser()` 在页面刷新时调用，从 token 恢复用户状态

- [x] **Step 3: 实现登录页面**

```vue
<!-- frontend/src/views/LoginView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <div class="w-full max-w-md p-8 bg-surface-container-low rounded-md">
      <h1 class="text-2xl font-semibold text-center mb-8"
STT 音频转录</h1>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
邮箱</label>
          <input
            v-model="form.email"
            type="email"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="your@email.com"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
密码</label>
          <input
            v-model="form.password"
            type="password"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div v-if="error" class="text-sm text-red-500"
{{ error }}</div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-3 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary-dim transition-colors disabled:opacity-50"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="text-center text-sm text-on-surface-variant mt-6"
        还没有账号？
        <RouterLink to="/register" class="text-primary hover:underline"
立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ email: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    await authStore.login(form.value)
    router.push({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
```

> **设计说明:**
> - 表单提交使用 `@submit.prevent` 阻止默认行为
> - 登录成功后跳转仪表盘，失败显示后端返回的错误信息
> - 按钮 loading 状态防止重复提交

- [x] **Step 4: 实现注册页面**

```vue
<!-- frontend/src/views/RegisterView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <div class="w-full max-w-md p-8 bg-surface-container-low rounded-md">
      <h1 class="text-2xl font-semibold text-center mb-8"
创建账号</h1>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
邮箱</label>
          <input
            v-model="form.email"
            type="email"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="your@email.com"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
真实姓名</label>
          <input
            v-model="form.real_name"
            type="text"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="张三"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
部门</label>
          <input
            v-model="form.department"
            type="text"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="技术部"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
密码</label>
          <input
            v-model="form.password"
            type="password"
            required
            minlength="6"
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
确认密码</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div v-if="error" class="text-sm text-red-500"
{{ error }}</div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-3 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary-dim transition-colors disabled:opacity-50"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="text-center text-sm text-on-surface-variant mt-6"
        已有账号？
        <RouterLink to="/login" class="text-primary hover:underline"
立即登录</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  email: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  department: '',
})
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  if (form.value.password !== form.value.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.register({
      email: form.value.email,
      password: form.value.password,
      real_name: form.value.real_name,
      department: form.value.department,
    })
    router.push({ name: 'login' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
```

> **设计说明:**
> - 前端做密码一致性校验，避免不必要的后端请求
> - 注册成功后跳转到登录页（而非自动登录），引导用户重新输入密码确认

- [x] **Step 5: 更新路由守卫**

修改 `frontend/src/router/index.ts`，在路由守卫中添加已登录用户的用户信息获取：

```typescript
import { useAuthStore } from '@/stores/auth'

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = !!localStorage.getItem('access_token')

  if (!to.meta.public && !isAuthenticated) {
    next({ name: 'login' })
    return
  }

  if (isAuthenticated && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      authStore.clearAuth()
      next({ name: 'login' })
      return
    }
  }

  next()
})
```

> **设计说明:**
> - 页面刷新时 token 仍在 localStorage，但 Pinia store 中的 user 会丢失
> - 路由守卫检测到 `access_token` 存在但 `user` 为空时，自动调用 `/me` 恢复用户状态
> - `/me` 失败（token 过期）时清除认证状态并跳转登录页

- [x] **Step 6: 提交**

```bash
git add frontend/src/api/auth.ts frontend/src/stores/auth.ts \
    frontend/src/views/LoginView.vue frontend/src/views/RegisterView.vue \
    frontend/src/router/index.ts
git commit -m "feat(task10): add auth API client and login/register pages"
```

---

## 阶段四：前端业务页面

### Task 11: 前端转录 API 模块

**Goal:** 创建前端转录相关的 API 数据层，定义 TypeScript 接口严格对齐后端 Pydantic Schema，实现上传、列表、详情、下载、删除等 API 调用函数，为 Task 12-14 的页面开发提供数据支持。

**Files:**
- Create: `frontend/src/api/transcription.ts`
- Modify: `backend/app/api/v1/transcription.py` — 补充 DELETE 路由

- [x] **Step 1: 定义 TypeScript 接口**

```typescript
// frontend/src/api/transcription.ts
export enum TranscriptionStatus {
  pending = 'pending',
  processing = 'processing',
  completed = 'completed',
  failed = 'failed',
}

export interface Transcription {
  id: string;
  user_id: string;
  filename: string;
  file_size: number;
  duration: number | null;
  language: string | null;
  status: TranscriptionStatus;
  model_used: string;
  created_at: string;
}

export interface TranscriptionResult {
  segments: Segment[];
  language: string;
  prompt_tokens: number;
  generation_tokens: number;
  total_tokens: number;
  prompt_tps: number;
  generation_tps: number;
  total_time: number;
}

export interface Segment {
  start_time: number;
  end_time: number;
  speaker_id: number | string;
  text: string;
}

export interface TranscriptionDetail extends Transcription {
  result_json: TranscriptionResult | null;
  result_text: string | null;
  error_message: string | null;
  completed_at: string | null;
}

export interface TranscriptionListResponse {
  items: Transcription[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
```

> **设计说明:**
> - 接口命名和字段与后端 `schemas/transcription.py` 严格对齐
> - `uuid.UUID` 在前端统一用 `string` 表示
> - `result_json` 细化为 `TranscriptionResult` 结构体，便于组件中类型安全地访问 `segments`

---

- [x] **Step 2: 实现 API 函数**

```typescript
import client from './client'

export async function createTranscription(
  file: File,
  options?: {
    language?: string;
    onProgress?: (percent: number) => void;
  }
): Promise<Transcription> {
  const formData = new FormData()
  formData.append('file', file)
  if (options?.language) {
    formData.append('language', options.language)
  }

  const { data } = await client.post('/v1/transcriptions', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (options?.onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        options.onProgress(percent)
      }
    },
  })
  return data
}

export async function listTranscriptions(
  params?: {
    page?: number;
    page_size?: number;
    status?: TranscriptionStatus;
  }
): Promise<TranscriptionListResponse> {
  const { data } = await client.get('/v1/transcriptions', { params })
  return data
}

export async function getTranscription(id: string): Promise<TranscriptionDetail> {
  const { data } = await client.get(`/v1/transcriptions/${id}`)
  return data
}

export async function downloadTranscription(
  id: string,
  format: 'json' | 'txt' | 'srt' | 'vtt' | 'zip'
): Promise<void> {
  const response = await client.get(`/v1/transcriptions/${id}/download`, {
    params: { format },
    responseType: 'blob',
  })

  const contentDisposition = response.headers['content-disposition']
  let filename = `${id}.${format}`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) filename = match[1]
  }

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function deleteTranscription(id: string): Promise<void> {
  await client.delete(`/v1/transcriptions/${id}`)
}
```

> **设计说明:**
> - `createTranscription` 使用 `FormData` 上传文件，`onUploadProgress` 提供进度回调给 UI
> - `downloadTranscription` 使用 `responseType: 'blob'` 接收二进制流，通过临时 `<a>` 标签触发浏览器下载
> - 从 `Content-Disposition` 头提取后端生成的文件名（基于原始文件名），fallback 使用 `id.format`
> - 所有函数复用已有的 `client.ts` axios 实例，自动处理 JWT 和 401 跳转

---

- [x] **Step 3: 补充后端 DELETE 路由**

```python
# backend/app/api/v1/transcription.py — 新增
import os

@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除转录记录及其关联的音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # 删除磁盘上的音频文件
    if os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)

    await db.delete(transcription)
    await db.commit()
```

> **设计说明:**
> - 先删文件再删记录，避免记录删除后找不到文件路径
> - `user_id` 校验确保只能删除自己的记录
> - 返回 204 No Content，符合 REST 删除规范

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/api/transcription.ts backend/app/api/v1/transcription.py
git commit -m "feat(task11): add frontend transcription API module with upload/list/detail/download/delete"
```

---

### Task 12: 转录工作台 Dashboard — 上传区 + 进度条 + 结果展示

**Goal:** 实现 Dashboard 页面，包含音频上传区（拖拽+点击）、转录状态可视化、转录结果展示（说话人+时间戳）、音频属性面板、多格式下载按钮组。支持上传后自动轮询状态，URL 同步 transcription ID，刷新不丢失当前任务。

**Files:**
- Modify: `frontend/src/views/DashboardView.vue` — 主页面容器
- Create: `frontend/src/components/UploadArea.vue` — 拖拽/点击上传组件
- Create: `frontend/src/components/TranscriptionViewer.vue` — 转录结果展示组件

- [x] **Step 1: 创建 UploadArea 组件**

```vue
<!-- frontend/src/components/UploadArea.vue -->
<template>
  <div class="space-y-4">
    <!-- 拖拽上传区 -->
    <div
      class="relative rounded-xl p-10 text-center transition-all duration-200 cursor-pointer"
      :class="[
        isDragging
          ? 'bg-primary/5 ring-2 ring-primary/30'
          : 'bg-surface-container-low hover:bg-surface-container',
      ]"
      @dragenter.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept=".wav,.mp3,.flac,.m4a,.ogg"
        @change="handleFileSelect"
      />
      <span
        class="material-symbols-outlined text-4xl mb-3"
        :class="isDragging ? 'text-primary' : 'text-on-surface-variant'"
      >
        upload_file
      </span>
      <p class="text-sm text-on-surface font-medium">
        {{ isDragging ? '松开以上传音频文件' : '拖拽音频文件到此处，或点击选择' }}
      </p>
      <p class="text-xs text-on-surface-variant mt-2">
        支持 WAV、MP3、FLAC、M4A、OGG，最大 500MB
      </p>
    </div>

    <!-- 已选文件 + 上传按钮 -->
    <div
      v-if="selectedFile"
      class="flex items-center justify-between bg-surface-container-lowest rounded-xl p-4"
    >
      <div class="flex items-center gap-3 min-w-0">
        <span class="material-symbols-outlined text-on-surface-variant">audio_file</span>
        <div class="min-w-0">
          <p class="text-sm font-medium text-on-surface truncate">{{ selectedFile.name }}</p>
          <p class="text-xs text-on-surface-variant">{{ formatFileSize(selectedFile.size) }}</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <div v-if="isUploading" class="w-32">
          <div class="h-1.5 bg-surface-container-high rounded-full overflow-hidden">
            <div
              class="h-full bg-primary rounded-full transition-all duration-300"
              :style="{ width: `${uploadProgress}%` }"
            />
          </div>
          <p class="text-xs text-on-surface-variant mt-1 text-right">{{ uploadProgress }}%</p>
        </div>

        <button
          v-else
          @click.stop="handleUpload"
          class="px-5 py-2 bg-gradient-to-br from-primary to-primary-dim text-white text-sm font-medium rounded-lg hover:shadow-lg hover:shadow-primary/20 transition-all active:scale-[0.98]"
        >
          开始转录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  upload: [file: File]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const isUploading = ref(false)
const uploadProgress = ref(0)

const MAX_SIZE_MB = 500

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) validateAndSetFile(input.files[0])
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) validateAndSetFile(file)
}

function validateAndSetFile(file: File) {
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    alert(`文件过大，最大支持 ${MAX_SIZE_MB}MB`)
    return
  }
  selectedFile.value = file
  isUploading.value = false
  uploadProgress.value = 0
}

function handleUpload() {
  if (!selectedFile.value) return
  isUploading.value = true
  emit('upload', selectedFile.value)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function reset() {
  selectedFile.value = null
  isUploading.value = false
  uploadProgress.value = 0
  if (fileInput.value) fileInput.value.value = ''
}

function setProgress(p: number) {
  uploadProgress.value = p
}

defineExpose({ reset, setProgress })
</script>
```

> **设计说明:**
> - 拖拽区用 `bg-surface-container-low`，hover 加深到 `bg-surface-container`，不用边框
> - 拖拽进入时用 `ring-2 ring-primary/30` 提供视觉反馈
> - 上传进度条使用 `surface-container-high` 背景 + `primary` 填充
> - 暴露 `reset()` 和 `setProgress()` 方法供父组件控制

---

- [x] **Step 2: 创建 TranscriptionViewer 组件**

```vue
<!-- frontend/src/components/TranscriptionViewer.vue -->
<template>
  <div v-if="transcription" class="space-y-6 mt-8">
    <!-- 状态指示器 -->
    <div class="flex items-center gap-3 px-5 py-3 rounded-xl" :class="statusBgClass">
      <span class="material-symbols-outlined">{{ statusIcon }}</span>
      <span class="text-sm font-medium">{{ statusText }}</span>
      <span v-if="transcription.error_message" class="text-xs text-red-600 ml-2">
        {{ transcription.error_message }}
      </span>
    </div>

    <!-- 两栏布局：左侧属性面板 + 右侧 Segments -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- 音频属性面板 -->
      <div class="lg:col-span-1 space-y-4">
        <div class="bg-surface-container-lowest rounded-xl p-5 space-y-4">
          <h3 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
            音频属性
          </h3>
          <div class="space-y-3">
            <InfoRow label="文件名" :value="transcription.filename" />
            <InfoRow label="文件大小" :value="formatFileSize(transcription.file_size)" />
            <InfoRow label="音频时长" :value="formatDuration(transcription.duration)" />
            <InfoRow label="检测语言" :value="transcription.language || '自动检测'" />
            <InfoRow label="转录模型" :value="transcription.model_used" />
            <InfoRow label="创建时间" :value="formatDate(transcription.created_at)" />
            <InfoRow
              v-if="transcription.completed_at"
              label="完成时间"
              :value="formatDate(transcription.completed_at)"
            />
          </div>
        </div>

        <!-- 下载按钮组（仅 completed） -->
        <div v-if="transcription.status === TranscriptionStatus.completed" class="space-y-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant px-1">
            导出结果
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="fmt in downloadFormats"
              :key="fmt"
              @click="handleDownload(fmt)"
              class="px-3 py-2 bg-surface-container-low hover:bg-surface-container text-xs font-medium text-on-surface rounded-lg transition-colors text-center"
            >
              {{ fmt.toUpperCase() }}
            </button>
          </div>
        </div>
      </div>

      <!-- Segments 列表 -->
      <div class="lg:col-span-3">
        <div
          v-if="transcription.status === TranscriptionStatus.completed && segments.length > 0"
          class="bg-surface-container-lowest rounded-xl p-6 space-y-6"
        >
          <div v-for="(seg, idx) in segments" :key="idx" class="group">
            <div class="flex items-start gap-4">
              <div class="shrink-0 pt-0.5">
                <span class="inline-block px-2 py-1 bg-surface-container-low text-xs font-mono text-on-surface-variant rounded-md">
                  {{ formatTime(seg.start) }} - {{ formatTime(seg.end) }}
                </span>
              </div>
              <div class="shrink-0">
                <span
                  class="inline-block px-3 py-1 text-xs font-medium rounded-full"
                  :class="speakerColorClass(seg.speaker)"
                >
                  {{ seg.speaker }}
                </span>
              </div>
              <p class="text-sm text-on-surface leading-relaxed flex-1">{{ seg.text }}</p>
            </div>
          </div>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.completed && transcription.result_text"
          class="bg-surface-container-lowest rounded-xl p-6"
        >
          <p class="text-sm text-on-surface leading-relaxed whitespace-pre-wrap">
            {{ transcription.result_text }}
          </p>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.processing"
          class="bg-surface-container-lowest rounded-xl p-12 flex flex-col items-center justify-center"
        >
          <div class="w-10 h-10 border-3 border-surface-container-high border-t-primary rounded-full animate-spin mb-4" />
          <p class="text-sm text-on-surface-variant">正在转录中，请稍候...</p>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.pending"
          class="bg-surface-container-lowest rounded-xl p-12 flex flex-col items-center justify-center"
        >
          <span class="material-symbols-outlined text-3xl text-on-surface-variant mb-3">schedule</span>
          <p class="text-sm text-on-surface-variant">任务已加入队列，等待处理...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  TranscriptionStatus,
  type TranscriptionDetail,
  downloadTranscription,
} from '@/api/transcription'

const props = defineProps<{
  transcription: TranscriptionDetail | null
}>()

const downloadFormats = ['json', 'txt', 'srt', 'vtt', 'zip'] as const

const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '转录中',
    completed: '已完成',
    failed: '转录失败',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const statusIcon = computed(() => {
  const map: Record<string, string> = {
    pending: 'schedule',
    processing: 'autorenew',
    completed: 'check_circle',
    failed: 'error',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const statusBgClass = computed(() => {
  const map: Record<string, string> = {
    pending: 'bg-surface-container-low text-on-surface-variant',
    processing: 'bg-primary/5 text-primary',
    completed: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const segments = computed(() => {
  if (!props.transcription?.result_json?.segments) return []
  return props.transcription.result_json.segments.map((seg) => ({
    start: seg.start_time,
    end: seg.end_time,
    speaker: `Speaker ${seg.speaker_id}`,
    text: seg.text,
  }))
})

const speakerColors: Record<string, string> = {
  'Speaker 0': 'bg-blue-50 text-blue-700',
  'Speaker 1': 'bg-purple-50 text-purple-700',
  'Speaker 2': 'bg-amber-50 text-amber-700',
  'Speaker 3': 'bg-emerald-50 text-emerald-700',
}

function speakerColorClass(speaker: string): string {
  return speakerColors[speaker] || 'bg-surface-container text-on-surface-variant'
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  return formatTime(seconds)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

async function handleDownload(format: string) {
  if (!props.transcription) return
  await downloadTranscription(
    props.transcription.id,
    format as 'json' | 'txt' | 'srt' | 'vtt' | 'zip'
  )
}
</script>
```

> **设计说明:**
> - 两栏布局：左侧 1/4 属性面板 + 下载按钮，右侧 3/4 转录内容
> - 说话人分色使用浅背景 + 深色文字（blue/purple/amber/emerald），确保可读性
> - 时间戳用等宽字体 + `surface-container-low` 背景标签
> - 状态指示器用背景色区分：processing 用 primary/5，completed 用 green-50，failed 用 red-50
> - 无 segment 数据时 fallback 展示纯文本结果

---

- [x] **Step 3: 实现 DashboardView 页面**

```vue
<!-- frontend/src/views/DashboardView.vue -->
<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-headline-sm font-semibold tracking-tight">转录工作台</h2>
      <p class="text-sm text-on-surface-variant mt-1">
        上传音频文件，系统将自动进行带说话人分离和时间戳的转录
      </p>
    </div>

    <UploadArea ref="uploadAreaRef" @upload="handleUpload" />
    <TranscriptionViewer :transcription="currentTranscription" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UploadArea from '@/components/UploadArea.vue'
import TranscriptionViewer from '@/components/TranscriptionViewer.vue'
import {
  createTranscription,
  getTranscription,
  type TranscriptionDetail,
} from '@/api/transcription'

const route = useRoute()
const router = useRouter()
const uploadAreaRef = ref<InstanceType<typeof UploadArea> | null>(null)

const currentTranscription = ref<TranscriptionDetail | null>(null)
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)

async function handleUpload(file: File) {
  try {
    const transcription = await createTranscription(file, {
      onProgress: (percent) => uploadAreaRef.value?.setProgress(percent),
    })
    currentTranscription.value = transcription as TranscriptionDetail
    uploadAreaRef.value?.reset()
    router.replace({ query: { t: transcription.id } })

    if (transcription.status !== 'completed' && transcription.status !== 'failed') {
      startPolling(transcription.id)
    }
  } catch (err: any) {
    alert(err.response?.data?.detail || '上传失败，请重试')
    uploadAreaRef.value?.reset()
  }
}

function startPolling(id: string) {
  stopPolling()
  pollTimer.value = setInterval(async () => {
    try {
      const data = await getTranscription(id)
      currentTranscription.value = data
      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling()
      }
    } catch {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(async () => {
  const id = route.query.t as string | undefined
  if (id) {
    try {
      const data = await getTranscription(id)
      currentTranscription.value = data
      if (data.status !== 'completed' && data.status !== 'failed') {
        startPolling(id)
      }
    } catch {
      router.replace({ query: {} })
    }
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>
```

> **设计说明:**
> - URL 同步：上传成功后更新 `?t=xxx`，刷新页面自动加载该转录并继续轮询
> - 轮询间隔 3 秒，completed/failed 时自动停止
> - 上传进度通过组件 ref 的 `setProgress` 回传，完成后 `reset()` 清空上传区
> - 页面加载时检查 URL 参数，无效 ID 自动清除参数

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/views/DashboardView.vue \
    frontend/src/components/UploadArea.vue \
    frontend/src/components/TranscriptionViewer.vue
git commit -m "feat(task12): add Dashboard with upload area, status polling, and transcription viewer"
```

> **关键设计决策:**
> - URL 同步 `?t=`：刷新不丢失当前转录任务
> - 轮询 3s 间隔：平衡实时性和服务端压力
> - 组件 ref 控制上传区：`reset()` + `setProgress()` 精确控制
> - 说话人 4 色循环：超过 4 个 fallback 灰色
> - 两栏 1:3 布局：大屏侧栏固定，小屏堆叠

---

### Task 13: 历史记录页 — 列表 + 搜索筛选 + 分页

**Goal:** 实现历史记录页面，支持按文件名搜索、按状态筛选、分页展示转录任务列表。每条记录展示文件名、创建时间、时长、状态和操作按钮（查看详情、下载结果、下载原始音频、删除）。同步补充后端搜索参数和原始音频下载端点。

**Files:**
- Create: `frontend/src/components/Pagination.vue` — 分页组件
- Modify: `frontend/src/views/HistoryView.vue` — 历史记录列表页
- Modify: `backend/app/api/v1/transcription.py` — 添加 search 参数和 `/audio` 端点

- [x] **Step 1: 创建 Pagination 组件**

```vue
<!-- frontend/src/components/Pagination.vue -->
<template>
  <div class="flex items-center justify-between">
    <p class="text-xs text-on-surface-variant">
      共 {{ totalItems }} 条，{{ totalPages }} 页
    </p>
    <div class="flex items-center gap-1">
      <button
        :disabled="currentPage <= 1"
        @click="$emit('update:page', currentPage - 1)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <span class="material-symbols-outlined text-sm">chevron_left</span>
      </button>

      <button
        v-for="page in visiblePages"
        :key="page"
        @click="$emit('update:page', page)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition-colors"
        :class="page === currentPage ? 'bg-primary text-white' : 'text-on-surface hover:bg-surface-container-low'"
      >
        {{ page }}
      </button>

      <button
        :disabled="currentPage >= totalPages"
        @click="$emit('update:page', currentPage + 1)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <span class="material-symbols-outlined text-sm">chevron_right</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  currentPage: number
  totalPages: number
  totalItems: number
}>()

defineEmits<{
  'update:page': [page: number]
}>()

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, props.currentPage - Math.floor(maxVisible / 2))
  let end = Math.min(props.totalPages, start + maxVisible - 1)
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})
</script>
```

> **设计说明:**
> - 当前页用 `bg-primary text-white` 高亮，其他页 hover 加深背景
> - 最多显示 5 个页码，自动滑动保持当前页居中
> - 上一页/下一页在边界时 disabled

---

- [x] **Step 2: 修改后端 API（搜索 + 原始音频下载）**

```python
# backend/app/api/v1/transcription.py

# 1. 在导入区添加 FileResponse
from fastapi.responses import FileResponse, StreamingResponse

# 2. 在 list_transcriptions 中添加 search 参数
@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TranscriptionStatus | None = Query(None),
    search: str | None = Query(None, description="按文件名搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    count_query = select(func.count()).select_from(Transcription).where(Transcription.user_id == current_user.id)

    if status:
        query = query.where(Transcription.status == status)
        count_query = count_query.where(Transcription.status == status)

    if search:
        query = query.where(Transcription.filename.ilike(f"%{search}%"))
        count_query = count_query.where(Transcription.filename.ilike(f"%{search}%"))

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

# 3. 添加原始音频下载端点（放在文件末尾）
@router.get("/{transcription_id}/audio")
async def download_audio(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载原始音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not os.path.exists(transcription.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        transcription.file_path,
        filename=transcription.filename,
        media_type="application/octet-stream",
    )
```

> **设计说明:**
> - `search` 参数使用 `ilike` 实现不区分大小写的模糊匹配
> - 原始音频下载使用 `FileResponse`，由 FastAPI 自动处理大文件流式传输
> - `media_type="application/octet-stream"` 强制浏览器下载而非预览

---

- [x] **Step 3: 实现 HistoryView 页面**

```vue
<!-- frontend/src/views/HistoryView.vue -->
<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-on-surface">历史记录</h2>
      <p class="text-sm text-on-surface-variant mt-1">查看和管理您的所有转录任务</p>
    </div>

    <!-- 搜索 + 状态筛选 -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span>
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="搜索文件名..."
          class="w-full pl-10 pr-4 py-2.5 bg-surface-container-lowest rounded-lg text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>
      <div class="flex gap-2">
        <button
          v-for="s in statusOptions"
          :key="s.value"
          @click="handleStatusChange(s.value)"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
          :class="currentStatus === s.value ? 'bg-primary text-white' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- 列表 -->
    <div class="space-y-2">
      <!-- 表头 -->
      <div class="hidden sm:grid sm:grid-cols-12 px-4 py-2">
        <span class="col-span-5 text-xs font-bold uppercase tracking-wider text-on-surface-variant">文件名</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant">创建时间</span>
        <span class="col-span-1 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-right">时长</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-center">状态</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-right">操作</span>
      </div>

      <!-- 列表项 -->
      <div
        v-for="item in items"
        :key="item.id"
        class="bg-surface-container-lowest rounded-xl p-4 flex flex-col sm:grid sm:grid-cols-12 sm:items-center gap-3 sm:gap-4 hover:bg-surface-container-low transition-colors"
      >
        <!-- 文件名 -->
        <div class="sm:col-span-5 flex items-center gap-3 min-w-0">
          <div class="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-on-surface-variant text-lg">audio_file</span>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-on-surface truncate">{{ item.filename }}</p>
            <p class="text-xs text-on-surface-variant">{{ formatFileSize(item.file_size) }}</p>
          </div>
        </div>

        <!-- 创建时间 -->
        <div class="sm:col-span-2 text-sm text-on-surface-variant">{{ formatDate(item.created_at) }}</div>

        <!-- 时长 -->
        <div class="sm:col-span-1 text-sm text-on-surface-variant text-right">{{ formatDuration(item.duration) }}</div>

        <!-- 状态 -->
        <div class="sm:col-span-2 flex justify-center">
          <span
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
            :class="statusTagClass(item.status)"
          >
            <span v-if="item.status === 'processing'" class="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />
            {{ statusLabel(item.status) }}
          </span>
        </div>

        <!-- 操作 -->
        <div class="sm:col-span-2 flex items-center justify-end gap-1">
          <button
            @click="viewDetail(item.id)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="查看详情"
          >
            <span class="material-symbols-outlined text-sm">visibility</span>
          </button>
          <button
            @click="downloadResult(item.id)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="下载结果"
          >
            <span class="material-symbols-outlined text-sm">description</span>
          </button>
          <button
            @click="downloadAudio(item.id, item.filename)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="下载原始音频"
          >
            <span class="material-symbols-outlined text-sm">music_note</span>
          </button>
          <button
            @click="confirmDelete(item)"
            class="p-1.5 text-on-surface-variant hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
            title="删除"
          >
            <span class="material-symbols-outlined text-sm">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="items.length === 0" class="py-16 text-center">
      <span class="material-symbols-outlined text-4xl text-on-surface-variant mb-3">history</span>
      <p class="text-sm text-on-surface-variant">暂无转录记录</p>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pt-2">
      <Pagination
        :current-page="currentPage"
        :total-pages="totalPages"
        :total-items="totalItems"
        @update:page="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Pagination from '@/components/Pagination.vue'
import {
  listTranscriptions,
  deleteTranscription,
  downloadTranscription,
  TranscriptionStatus,
  type Transcription,
} from '@/api/transcription'

const router = useRouter()

const items = ref<Transcription[]>([])
const currentPage = ref(1)
const totalPages = ref(0)
const totalItems = ref(0)
const currentStatus = ref<string>('')
const searchQuery = ref('')
const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const statusOptions = [
  { value: '', label: '全部' },
  { value: TranscriptionStatus.pending, label: '等待中' },
  { value: TranscriptionStatus.processing, label: '转录中' },
  { value: TranscriptionStatus.completed, label: '已完成' },
  { value: TranscriptionStatus.failed, label: '失败' },
]

onMounted(() => {
  loadData()
})

async function loadData() {
  try {
    const params: Record<string, any> = { page: currentPage.value, page_size: 10 }
    if (currentStatus.value) params.status = currentStatus.value
    if (searchQuery.value) params.search = searchQuery.value
    const data = await listTranscriptions(params)
    items.value = data.items
    totalPages.value = data.pages
    totalItems.value = data.total
  } catch {
    alert('加载失败，请重试')
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadData()
}

function handleStatusChange(status: string) {
  currentStatus.value = status
  currentPage.value = 1
  loadData()
}

function handleSearch() {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  searchTimer.value = setTimeout(() => {
    currentPage.value = 1
    loadData()
  }, 300)
}

function viewDetail(id: string) {
  router.push({ name: 'transcription-detail', params: { id } })
}

function downloadResult(id: string) {
  downloadTranscription(id, 'zip')
}

function downloadAudio(id: string, filename: string) {
  const link = document.createElement('a')
  link.href = `/api/v1/transcriptions/${id}/audio`
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
}

async function confirmDelete(item: Transcription) {
  if (!confirm(`确定要删除 "${item.filename}" 吗？此操作不可恢复。`)) return
  try {
    await deleteTranscription(item.id)
    loadData()
  } catch {
    alert('删除失败')
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN')
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    processing: '转录中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusTagClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'bg-slate-100 text-slate-600',
    processing: 'bg-blue-50 text-blue-700',
    completed: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
  }
  return map[status] || 'bg-surface-container text-on-surface-variant'
}
</script>
```

> **设计说明:**
> - 列表采用卡片形式（`bg-surface-container-lowest rounded-xl`），行之间用 `gap-2` 分隔，无 1px 边框
> - 响应式：小屏时堆叠显示，大屏时用 `grid-cols-12` 对齐列
> - 搜索 300ms debounce，减少不必要的 API 请求
> - 状态切换和页码切换时重置到第一页
> - 操作按钮使用图标 + title，hover 时显示主色/红色反馈
> - 空状态居中展示，带图标和提示文字

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/components/Pagination.vue \
    frontend/src/views/HistoryView.vue \
    backend/app/api/v1/transcription.py
git commit -m "feat(task13): add History page with search, status filter, pagination, and audio download"
```

> **关键设计决策:**
> - 后端搜索用 `ilike` 模糊匹配，避免前端分页+搜索的数据不完整问题
> - 原始音频下载用 `FileResponse` 流式传输，避免大文件内存占用
> - 卡片列表替代传统表格，遵循设计系统"无边框"原则
> - 操作按钮图标化，节省空间，title 提供可访问性提示

---

### Task 14: 转录详情页 — 说话人分色 + 时间戳 + 下载

**Goal:** 实现转录详情页面，从路由参数获取转录 ID，加载详情数据，展示音频播放器（completed 状态）、转录结果（复用 TranscriptionViewer）、返回按钮。支持从 Dashboard 和 History 页面跳转进入。

**Files:**
- Modify: `frontend/src/views/TranscriptionDetailView.vue`

- [x] **Step 1: 实现 TranscriptionDetailView.vue**

```vue
<!-- frontend/src/views/TranscriptionDetailView.vue -->
<template>
  <div class="space-y-6">
    <!-- 返回栏 + 标题 -->
    <div class="flex items-center gap-4">
      <button
        @click="goBack"
        class="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg transition-colors"
      >
        <span class="material-symbols-outlined">arrow_back</span>
      </button>
      <div class="min-w-0">
        <h2 class="text-xl font-semibold tracking-tight text-on-surface truncate">
          {{ transcription?.filename || '转录详情' }}
        </h2>
        <p v-if="statusText" class="text-sm text-on-surface-variant mt-0.5">{{ statusText }}</p>
      </div>
    </div>

    <!-- 音频播放器 -->
    <div
      v-if="transcription?.status === 'completed'"
      class="bg-surface-container-lowest rounded-xl p-4"
    >
      <audio :src="audioUrl" controls class="w-full" />
    </div>

    <!-- 转录结果 -->
    <TranscriptionViewer :transcription="transcription" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TranscriptionViewer from '@/components/TranscriptionViewer.vue'
import { getTranscription, type TranscriptionDetail } from '@/api/transcription'

const route = useRoute()
const router = useRouter()

const transcription = ref<TranscriptionDetail | null>(null)
const loading = ref(false)

const statusText = computed(() => {
  if (!transcription.value) return ''
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '转录中',
    completed: '已完成',
    failed: '转录失败',
  }
  return map[transcription.value.status] || ''
})

const audioUrl = computed(() => {
  if (!transcription.value) return ''
  return `/api/v1/transcriptions/${transcription.value.id}/audio`
})

onMounted(async () => {
  const id = route.params.id as string
  if (!id) {
    router.push({ name: 'history' })
    return
  }

  loading.value = true
  try {
    const data = await getTranscription(id)
    transcription.value = data
  } catch {
    alert('加载转录详情失败')
    router.push({ name: 'history' })
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.back()
}
</script>
```

> **设计说明:**
> - 复用 `TranscriptionViewer` 组件展示转录结果，保持 Dashboard 和详情页展示一致性
> - 音频播放器仅 completed 状态显示，使用原生 `<audio>` 标签
> - 返回按钮使用 `router.back()`，兼容从 Dashboard 或 History 页面进入的场景
> - 加载失败自动跳转到历史记录页，避免用户停留在错误状态
> - 页面标题显示原始文件名，下方小字显示状态

---

- [x] **Step 2: 提交**

```bash
git add frontend/src/views/TranscriptionDetailView.vue
git commit -m "feat(task14): add Transcription Detail page with audio player and back navigation"
```

> **设计说明:**
> - 详情页无独立组件拆分，直接复用 TranscriptionViewer 保持代码复用
> - 音频播放地址复用 Task 13 新增的 `/audio` 端点
> - 路由参数 `/:id` 已在 Task 9 的 router 中定义，无需修改

---

## 阶段五：集成与收尾

### Task 15: 前后端联调 + 健康检查 + 错误处理 + .gitignore

**Goal:** 项目收尾，完善 .gitignore 防止敏感文件泄露，增强后端健康检查（数据库 + Redis），增强前端 API 超时和错误处理，确保前后端联调顺畅。

**Files:**
- Modify: `.gitignore` — 补充 Claude Code 临时文件和前端环境变量
- Modify: `backend/app/main.py` — 增强健康检查端点
- Modify: `frontend/src/api/client.ts` — 添加请求超时

- [x] **Step 1: 完善 .gitignore**

```gitignore
# 追加到 .gitignore 末尾

# Claude Code 会话数据
.claude/

# 前端环境变量
frontend/.env
frontend/.env.local
frontend/.env.*.local
```

> **设计说明:**
> - `.claude/` 是 Claude Code 生成的临时文件目录，含会话缓存，不应提交
> - 前端 `.env*` 文件可能含 API 密钥等敏感配置，统一忽略

---

- [x] **Step 2: 增强后端健康检查**

```python
# backend/app/main.py — 修改 health_check
from sqlalchemy import text

@app.get("/api/health")
async def health_check():
    health = {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
    }

    # 检查数据库连接
    try:
        from app.database import async_session
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        health["database"] = "ok"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "degraded"

    # 检查 Redis 连接
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        r.ping()
        r.close()
        health["redis"] = "ok"
    except Exception as e:
        health["redis"] = f"error: {str(e)}"
        health["status"] = "degraded"

    return health
```

> **设计说明:**
> - 健康检查返回 JSON 包含各子系统状态，任一失败标记 `status` 为 `degraded`
> - Redis 检查使用 `socket_connect_timeout=2` 避免阻塞过长时间
> - 数据库使用 `SELECT 1` 轻量查询验证连接可用性

---

- [x] **Step 3: 增强前端 API 超时配置**

```typescript
// frontend/src/api/client.ts
const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000, // 30 秒超时，覆盖上传/下载等大请求
})
```

> **设计说明:**
003e - 30 秒超时覆盖大多数场景：文件上传可能超过默认的无限等待，但 30 秒足够处理 500MB 文件
> - 下载请求（zip 打包）如果超过 30 秒，浏览器会自动处理，axios 拦截器不影响 blob 下载

---

- [x] **Step 4: 提交**

```bash
git add .gitignore backend/app/main.py frontend/src/api/client.ts
git commit -m "feat(task15): enhance health checks, gitignore, and API timeout"
```

> **收尾清单（手动验证）:**> - [x] 访问 `http://localhost:8000/api/health` 返回包含 `database` 和 `redis` 字段的 JSON
> - [x] 确认 `.gitignore` 忽略 `.claude/` 和前端 `.env` 文件
> - [x] 确认前端 `npm run dev` 无编译错误
> - [x] 确认后端 `uvicorn app.main:app --reload` 正常启动
