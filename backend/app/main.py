import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from pathlib import Path

from app.api.v1 import api_router
from app.config import settings
from app.logging_config import request_id_ctx, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
app.include_router(api_router)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """为每个请求生成 request_id，注入日志上下文，并附加到响应头."""
    request_id = str(uuid.uuid4())[:8]
    request_id_ctx.set(request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    """捕获所有未处理的异常，记录到 error.log 后再抛出."""
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(
            "Unhandled exception at %s %s: %s",
            request.method,
            request.url.path,
            exc,
        )
        raise

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