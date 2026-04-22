# 在线音频转录网站 — 设计规格文档

## 概述

基于现有 `transcribe_demo.py`（mlx-audio + VibeVoice-ASR）构建面向公众的在线转录网站。用户上传音频文件，系统进行带说话人分离和时间戳的转录，结果支持多种格式下载。

**技术栈**：FastAPI (Python) + Vue3 SPA + PostgreSQL + Celery + Redis

**设计系统**："The Sonic Gallery" — 基于 `stitch_minimal_audio_transcription/` 参考设计适配

## 需求

- 公开服务，完整用户注册/登录体系（先做邮箱注册，后续扩展 OAuth）
- 文件上传转录，支持说话人分离 + 时间戳
- 中英文双语，自动检测语言
- 输出格式：JSON、SRT、VTT、纯文本（支持多格式打包 zip 下载）
- 历史记录列表，支持搜索、筛选、重新下载原始音频
- 用户资料包含真实姓名和部门（面向内部/企业使用场景）

## 架构

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   Vue3 SPA  │────▶│   FastAPI    │────▶│   Celery      │
│  (前端)      │◀────│  (REST API)  │     │   Worker      │
└─────────────┘     └──────┬───────┘     └───────┬───────┘
                           │                      │
                    ┌──────▼───────┐       ┌──────▼───────┐
                    │  PostgreSQL  │       │    Redis     │
                    │  (数据存储)   │       │  (消息队列)   │
                    └──────────────┘       └──────────────┘
                                                   │
                                           ┌───────▼───────┐
                                           │  mlx-audio    │
                                           │  VibeVoice    │
                                           │  (转录引擎)    │
                                           └───────────────┘
```

### 数据流

1. 用户上传音频 → FastAPI 接收并存文件 → 创建 Transcription 记录 (pending) → 发送到 Redis 队列
2. Celery Worker 取任务 → 调用 mlx-audio VibeVoice → 结果写入数据库
3. 前端轮询/SSE 获取任务状态 → 展示结果

### 目录结构

```
stt_qzqzqqz/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── models/        # SQLAlchemy 模型
│   │   ├── api/           # 路由处理器
│   │   ├── services/      # 业务逻辑
│   │   ├── tasks/         # Celery 任务
│   │   └── schemas/       # Pydantic 模式
│   ├── alembic/           # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   ├── components/
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── api/           # API 调用
│   │   └── router/
│   └── package.json
├── transcribe_demo.py     # 原始 demo（保留）
└── docker-compose.yml
```

## 数据模型

### 用户表 (User)

| 字段        | 类型     | 约束              |
|-------------|----------|-------------------|
| id          | UUID     | 主键              |
| email       | String   | 唯一，索引        |
| password    | String   | bcrypt 哈希       |
| real_name   | String   | 必填              |
| department  | String   | 必填              |
| phone       | String   | 可选              |
| is_active   | Boolean  | 默认 True         |
| created_at  | DateTime | 自动生成          |

### 转录任务表 (Transcription)

| 字段          | 类型     | 约束                                   |
|---------------|----------|-----------------------------------------|
| id            | UUID     | 主键                                    |
| user_id       | UUID     | 外键 → User                             |
| filename      | String   | 原始文件名                              |
| file_path     | String   | 服务端存储路径                          |
| file_size     | Integer  | 字节数                                  |
| duration      | Float    | 音频时长（秒）                          |
| language      | String   | 检测到的语言 (zh/en)                    |
| status        | Enum     | pending / processing / completed / failed |
| model_used    | String   | 模型名（如 VibeVoice-ASR-bf16）         |
| result_json   | JSON     | 结构化结果（说话人+时间戳+内容）         |
| result_text   | Text     | 纯文本结果                              |
| error_message | Text     | 失败原因                                |
| created_at    | DateTime | 自动生成                                |
| completed_at  | DateTime | 可空                                    |

**设计决策**：
- `result_json` 存储原始结构化数据；SRT/VTT 从中动态生成，不单独存储
- 音频文件存本地磁盘，通过 `file_path` 记录路径（后续可迁移至对象存储）

## API 设计

### 认证模块

| 方法 | 端点                  | 说明                                |
|------|-----------------------|-------------------------------------|
| POST | /api/auth/register    | 注册（邮箱+密码+姓名+部门）         |
| POST | /api/auth/login       | 登录，返回 JWT                      |
| POST | /api/auth/refresh     | 刷新 token                          |
| GET  | /api/auth/me          | 获取当前用户信息                    |

### 转录模块

| 方法   | 端点                                                | 说明                                          |
|--------|-----------------------------------------------------|-----------------------------------------------|
| POST   | /api/transcriptions                                 | 上传音频，创建转录任务                        |
| GET    | /api/transcriptions                                 | 获取当前用户的转录列表（分页）                |
| GET    | /api/transcriptions/{id}                            | 获取转录详情 + 结果                           |
| GET    | /api/transcriptions/{id}/download?formats=srt,vtt,txt,json | 下载：单格式直接返回文件，多格式打包 zip      |
| GET    | /api/transcriptions/{id}/audio                      | 重新下载原始音频文件                          |
| DELETE | /api/transcriptions/{id}                            | 删除转录记录 + 文件                           |

### 通用

| 方法 | 端点         | 说明     |
|------|--------------|----------|
| GET  | /api/health  | 健康检查 |

**认证细节**：JWT 方案，access_token 30分钟过期 + refresh_token 7天过期。上传限制 500MB，支持格式：wav/mp3/flac/m4a/ogg。列表接口支持按状态、日期筛选，按创建时间倒序分页。

## 前端设计

### 设计系统："The Sonic Gallery"

基于 `stitch_minimal_audio_transcription/` 参考设计适配。核心原则：

- **字体**：仅使用 Inter
- **主色**：`#0053db`（信号蓝）
- **表面层级**：`#f7f9fb` → `#f0f4f7` → `#e8eff3` → `#d9e4ea`
- **无边框规则**：用背景色差（2%色差）分层，不使用 1px 边框
- **毛玻璃导航**：`backdrop-blur-xl` + 半透明背景
- **图标**：Material Symbols Outlined
- **CSS 框架**：Tailwind CSS
- **排版**：Display-lg (3.5rem) 用于空状态，headline-sm (1.5rem, 紧凑字距) 用于标题，body-lg (1rem, 行高 1.6) 用于转录文本，label-md (0.75rem) 用于时间戳/元数据
- **按钮**：主按钮（primary 到 primary-dim 渐变，135度），次按钮（secondary-container 背景），三级按钮（仅文字）
- **层级**：优先使用色阶分层而非阴影；环境阴影使用 `rgba(42,52,57,0.06)`，不用纯黑

### 页面规划

| 页面           | 参考来源       | 适配调整                                                    |
|----------------|----------------|-------------------------------------------------------------|
| 登录页         | _3             | 去掉社交登录（预留位置后续扩展），加"记住我"选项            |
| 注册页         | 基于 _3 扩展   | 增加真实姓名、部门、确认密码字段                            |
| 首页/转录页    | _1             | 去掉装饰性图片卡片和"智能摘要"；保留上传区+进度条+转录结果+音频属性面板 |
| 历史记录页     | _2             | 基本照用；增加"下载原始音频"操作按钮                        |
| 转录详情页     | 基于 _1 转录区 | 全幅转录内容，说话人分色显示，时间戳标签，顶部多格式下载按钮组 |

### 布局结构（已登录页面）

- **左侧栏**（w-64，固定）：品牌、导航（仪表盘、历史记录）、帮助、退出
- **顶部栏**（h-16，固定）：项目上下文、通知、用户头像
- **主内容区**：可滚动，max-w-7xl 居中

### 从参考设计中移除的内容

- 右侧装饰性抽象图片卡片（_1 中的）
- "Smart Summary / Generate Full Brief" 功能
- 社交登录按钮（仅预留位置，后续扩展）
- 转录结果上的 "Confidence" 置信度标签

## 转录引擎

- **默认模型**：`mlx-community/VibeVoice-ASR-bf16`
- **调用方式**：Celery Worker 调用 `mlx_audio.stt` API
- **说话人分离**：VibeVoice 原生支持，返回 JSON 包含 Speaker + Start/End + Content
- **语言检测**：自动检测或传入 `language` 参数
- **长音频**：VibeVoice 支持最长 60 分钟

### 异步任务流程

```
上传 → FastAPI 接收文件
    → 保存到磁盘 (uploads/{user_id}/{uuid}.wav)
    → 创建 Transcription 记录 (status=pending)
    → 发送任务到 Redis 队列
    → 返回 task_id 给前端

Celery Worker 取任务
    → 更新 status=processing
    → 调用 mlx-audio 转录
    → 解析结果，提取 segments
    → 生成纯文本 (result_text)
    → 存储结构化 JSON (result_json)
    → 更新 status=completed, completed_at=当前时间
    → 失败时：status=failed, error_message=异常信息

前端轮询 GET /api/transcriptions/{id}
    → pending/processing → 显示进度
    → completed → 渲染结果
    → failed → 显示错误信息
```

### 下载格式生成

- **纯文本**：直接返回 `result_text`
- **JSON**：直接返回 `result_json`
- **SRT/VTT**：从 `result_json` 的 segments 动态生成，不持久化
- **多格式打包**：用 `zipfile` 在内存中打包，流式返回