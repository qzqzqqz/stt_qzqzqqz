from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path

from app.api.v1 import api_router
from app.config import settings

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
    return {"status": "ok", "app": settings.APP_NAME}