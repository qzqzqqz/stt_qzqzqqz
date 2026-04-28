# Task 3: Docker Compose — PostgreSQL + Redis

> 所属阶段: 阶段一：项目基础设施


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

- [x] **Step 2: 创建 backend/.dockerignore**

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

- [x] **Step 3: 创建 backend/Dockerfile**

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
