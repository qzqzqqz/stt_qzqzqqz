# Task 17: 日志轻量改进 — 过滤噪音 + 请求上下文 + 格式统一

> 所属阶段: 阶段五：集成与收尾


**Goal:** 解决当前日志框架的嘈点问题，让日志更干净、更可追踪，同时不引入额外依赖。

**当前问题：**
1. `app.log` 被 SQLAlchemy 引擎日志淹没，真正的业务日志难以查找
2. 同一请求的多个日志无法关联，排查问题时难以定位
3. uvicorn 访问日志格式与业务日志不统一
4. Celery 日志会同时进入 `celery.log` 和 `app.log`

**Files:**
- Modify: `backend/app/logging_config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/celery_app.py`

- [x] **Step 1: 过滤 SQLAlchemy 引擎日志**

将 SQLAlchemy 引擎日志级别设为 WARNING，避免 `app.log` 被 SQL 语句淹没：

```python
# backend/app/logging_config.py — setup_logging() 中新增
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
```

> 说明：保留 WARNING 以上级别（连接失败等），过滤掉 INFO 级别的 `SELECT 1`、`ROLLBACK` 等常规 SQL。

- [x] **Step 2: 统一 uvicorn 访问日志格式**

配置 uvicorn 使用与业务日志相同的格式：

```python
# backend/app/logging_config.py
uvicorn_access = logging.getLogger("uvicorn.access")
uvicorn_access.handlers = []  # 清除默认 handler
uvicorn_access.addHandler(app_handler)  # 使用统一的 app_handler
uvicorn_access.setLevel(logging.INFO)
```

> 说明：uvicorn 默认的访问日志格式是 `127.0.0.1 - GET /api/health HTTP/1.1 200 OK`，统一后变为 `2026-05-06 10:23:45 | INFO | uvicorn.access | 127.0.0.1 GET /api/health 200`。

- [x] **Step 3: 添加 request_id 上下文中间件**

在 `main.py` 中添加中间件，为每个请求生成唯一 ID，并注入到日志上下文中：

```python
# backend/app/main.py
import uuid
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    request_id_ctx.set(request_id)
    # 将 request_id 附加到响应头，方便前端排查
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

> 说明：`ContextVar` 是线程/协程安全的上下文变量，确保同一请求内的所有日志都带相同的 request_id。

- [x] **Step 4: 改造日志格式，支持 request_id**

修改 `logging_config.py` 中的 `LOG_FORMAT`，通过 Filter 动态注入 request_id：

```python
# backend/app/logging_config.py
from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s"
```

然后在每个 handler 上添加这个 Filter：

```python
request_id_filter = RequestIdFilter()
app_handler.addFilter(request_id_filter)
error_handler.addFilter(request_id_filter)
# ... 所有 handler 都添加
```

> 说明：改造后日志示例：
> ```
> 2026-05-06 10:23:45 | INFO  | app.api.v1.auth | req=abc123de | User registered: qizhao@example.com
> 2026-05-06 10:23:47 | INFO  | app.api.v1.transcription | req=def456gh | Transcription created: uuid-xxx (test.mp3)
> ```

- [x] **Step 5: 修复 Celery 日志重复**

`app.tasks` 的日志既进入 `celery.log`（直接 handler）又进入 `app.log`（通过 root logger propagate）。解决方式：

```python
# backend/app/logging_config.py
celery_logger = logging.getLogger("app.tasks")
celery_logger.addHandler(celery_handler)
celery_logger.setLevel(logging.INFO)
celery_logger.propagate = False  # 阻止进入 root logger → app.log
```

> 说明：`propagate = False` 后，Celery 日志只进入 `celery.log`，不再重复进入 `app.log`。

- [x] **Step 6: 验证日志输出**

启动后端，发送几个请求，检查：
1. `app.log` 中**没有** SQLAlchemy 的 `SELECT 1` / `ROLLBACK` 日志
2. `app.log` 中每条日志都带 `req=xxxx` 前缀
3. uvicorn 访问日志格式与业务日志一致
4. `celery.log` 有内容但 `app.log` 中**没有**重复的 Celery 日志
5. 响应头中有 `X-Request-ID`

- [x] **Step 7: 提交代码**

```bash
git add backend/app/logging_config.py backend/app/main.py backend/app/celery_app.py
git commit -m "feat(task17): improve logging - filter noise, add request_id, unify format"
```

---