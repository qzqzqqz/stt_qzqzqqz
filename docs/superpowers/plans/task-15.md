# Task 15: 前后端联调 + 健康检查 + 错误处理 + .gitignore

> 所属阶段: 阶段五：集成与收尾


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
