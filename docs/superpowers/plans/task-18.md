# Task 18: 结构化日志（可选）— JSON 输出 + loguru 替换

> 所属阶段: 阶段五：集成与收尾
> **优先级: 低** — 当前阶段非必须，但为后续日志分析系统（ELK/Loki）做铺垫。


**Goal:** 将日志从纯文本格式升级为结构化 JSON 格式，便于后续接入日志收集和分析系统。

**为什么选这个方案？**

当前纯文本日志：
```
2026-05-06 10:23:45 | INFO  | app.api.v1.auth | req=abc123de | User registered: qizhao@example.com
```

需要写正则才能提取字段（时间、级别、模块、request_id、消息）。如果接入 ELK/Loki 等系统，纯文本需要额外配置解析规则。

结构化 JSON 日志：
```json
{"timestamp": "2026-05-06T10:23:45.123+08:00", "level": "INFO", "module": "app.api.v1.auth", "request_id": "abc123de", "message": "User registered: qizhao@example.com"}
```

日志系统可以直接按字段索引和搜索，无需正则解析。

**技术选型：loguru**

- 比标准库 `logging` API 更简洁（`logger.info("msg")` 即可，无需 `getLogger(__name__)`）
- 原生支持 JSON 序列化
- 自动处理异常 traceback（比 `logger.exception` 更美观）
- 内置文件轮转（不需要 `TimedRotatingFileHandler`）
- 与标准库 `logging` 兼容（可以桥接 uvicorn、SQLAlchemy 等第三方库的日志）

**Files:**
- Modify: `backend/requirements.txt` — 新增 `loguru`
- Replace: `backend/app/logging_config.py` — 改用 loguru
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`
- Modify: `backend/app/api/v1/*.py` — 改用 loguru logger

- [ ] **Step 1: 安装 loguru**

```bash
pip install loguru
```

- [ ] **Step 2: 重写 logging_config.py 为 loguru 版本**

配置三个 sink（输出目标）：
- `app.log` — 应用日志（INFO+），JSON 格式
- `celery.log` — Celery 任务日志（INFO+），JSON 格式
- `error.log` — 错误日志（ERROR+），JSON 格式，保留 30 天

```python
# backend/app/logging_config.py
from loguru import logger
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

def setup_logging():
    # 移除默认的 stderr sink
    logger.remove()
    
    # 控制台输出（开发时使用，保留颜色）
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> | <level>{message}</level>",
        level="INFO",
    )
    
    # app.log — JSON 格式
    logger.add(
        LOG_DIR / "app.log",
        format="{time} | {level} | {name} | {message}",
        level="INFO",
        rotation="00:00",  # 每天零点轮转
        retention="7 days",
        serialize=True,  # JSON 输出
        filter=lambda record: record["name"].startswith("app") and not record["name"].startswith("app.tasks"),
    )
    
    # celery.log — JSON 格式
    logger.add(
        LOG_DIR / "celery.log",
        format="{time} | {level} | {name} | {message}",
        level="INFO",
        rotation="00:00",
        retention="7 days",
        serialize=True,
        filter=lambda record: record["name"].startswith("app.tasks"),
    )
    
    # error.log — JSON 格式
    logger.add(
        LOG_DIR / "error.log",
        format="{time} | {level} | {name} | {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        serialize=True,
    )
    
    # 桥接标准库 logging → loguru（让 uvicorn、SQLAlchemy 的日志也走 loguru）
    from loguru import logger as loguru_logger
    import logging
    
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            level = loguru_logger.level(record.levelname).name if record.levelname in loguru_logger._core.levels else record.levelno
            loguru_logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())
    
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
```

- [ ] **Step 3: 更新 API 路由使用 loguru**

```python
# backend/app/api/v1/auth.py
from loguru import logger

# 去掉 import logging; logger = logging.getLogger(__name__)
# 直接使用 loguru 的 logger

@router.post("/register")
async def register(...):
    ...
    logger.info("User registered: {}", user.email)
    return user
```

> 说明：loguru 的 logger 是全局单例，不需要 `getLogger(__name__)`，直接使用 `from loguru import logger` 即可。模块名会自动从调用栈推断。

- [ ] **Step 4: 更新异常中间件**

```python
# backend/app/main.py
from loguru import logger

@app.middleware("http")
async def log_exceptions(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.exception(
            "Unhandled exception at {} {}: {}",
            request.method,
            request.url.path,
            exc,
        )
        raise
```

- [ ] **Step 5: 更新 requirements.txt**

```
loguru>=0.7.0
```

- [ ] **Step 6: 验证 JSON 日志输出**

启动后端，发送请求，检查 `app.log` 内容是否为 JSON：

```json
{"text": "2026-05-06 10:23:45 | INFO | app.api.v1.auth | User registered: qizhao@example.com\n", "record": {"elapsed": {"repr": "0:00:01.234567", "seconds": 1.234567}, "exception": null, "extra": {}, "file": {"name": "auth.py", "path": "/.../auth.py"}, "function": "register", "level": {"icon": "ℹ️", "name": "INFO", "no": 20}, "line": 35, "message": "User registered: qizhao@example.com", "module": "app.api.v1.auth", "name": "app.api.v1.auth", "process": {"id": 12345, "name": "MainProcess"}, "thread": {"id": 123456789, "name": "MainThread"}, "time": {"repr": "2026-05-06 10:23:45.123456+08:00", "timestamp": 1714967025.123456}}}
```

---

**与 Task 17 的关系：**

- Task 17（轻量改进）使用 Python 标准库，**零额外依赖**，解决当前日志的嘈点
- Task 18（结构化日志）使用 `loguru`，**新增一个依赖**，为后续日志分析系统做准备

**建议执行顺序：**
1. 先完成 Task 17（轻量改进）→ 立即获得干净的、带 request_id 的日志
2. 等项目上线后，如果需要接入 ELK/Loki 等日志系统，再执行 Task 18（结构化日志）