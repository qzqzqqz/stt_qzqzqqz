# Task 2: 数据库 — SQLAlchemy 模型 + Alembic 迁移

> 所属阶段: 阶段一：项目基础设施


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

- [x] **Step 8: 生成初始迁移脚本**

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz/backend
alembic revision --autogenerate -m "create users and transcriptions tables"
```

检查生成的迁移文件，确认包含：
- `users` 表（id, email, password, real_name, department, phone, is_active, created_at）
- `transcriptions` 表（id, user_id FK, filename, file_path, file_size, duration, language, status enum, model_used, result_json, result_text, error_message, created_at, completed_at）
- `transcriptionstatus` 枚举类型
- 相应的索引（email unique, user_id index, status index）

- [x] **Step 9: 提交**

```bash
git add backend/app/database.py backend/app/models/ backend/alembic/ backend/alembic.ini
git commit -m "feat: add SQLAlchemy models (User, Transcription) and Alembic migration setup"
```

> 注意：此时 **不执行** `alembic upgrade head`，因为 PostgreSQL 还没启动（Task 3 会用 Docker Compose 启动）。迁移脚本的生成不需要数据库连接，但执行迁移需要。

---
