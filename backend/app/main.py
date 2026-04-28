from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from pathlib import Path

from app.api.v1 import api_router
from app.config import settings
from app.logging_config import setup_logging

setup_logging()

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
app.include_router(api_router)

# 确保上传目录存在
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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