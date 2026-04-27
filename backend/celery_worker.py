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