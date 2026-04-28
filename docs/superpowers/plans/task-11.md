# Task 11: 前端转录 API 模块

> 所属阶段: 阶段四：前端业务页面


**Goal:** 创建前端转录相关的 API 数据层，定义 TypeScript 接口严格对齐后端 Pydantic Schema，实现上传、列表、详情、下载、删除等 API 调用函数，为 Task 12-14 的页面开发提供数据支持。

**Files:**
- Create: `frontend/src/api/transcription.ts`
- Modify: `backend/app/api/v1/transcription.py` — 补充 DELETE 路由

- [x] **Step 1: 定义 TypeScript 接口**

```typescript
// frontend/src/api/transcription.ts
export enum TranscriptionStatus {
  pending = 'pending',
  processing = 'processing',
  completed = 'completed',
  failed = 'failed',
}

export interface Transcription {
  id: string;
  user_id: string;
  filename: string;
  file_size: number;
  duration: number | null;
  language: string | null;
  status: TranscriptionStatus;
  model_used: string;
  created_at: string;
}

export interface TranscriptionResult {
  segments: Segment[];
  language: string;
  prompt_tokens: number;
  generation_tokens: number;
  total_tokens: number;
  prompt_tps: number;
  generation_tps: number;
  total_time: number;
}

export interface Segment {
  start_time: number;
  end_time: number;
  speaker_id: number | string;
  text: string;
}

export interface TranscriptionDetail extends Transcription {
  result_json: TranscriptionResult | null;
  result_text: string | null;
  error_message: string | null;
  completed_at: string | null;
}

export interface TranscriptionListResponse {
  items: Transcription[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}
```

> **设计说明:**
> - 接口命名和字段与后端 `schemas/transcription.py` 严格对齐
> - `uuid.UUID` 在前端统一用 `string` 表示
> - `result_json` 细化为 `TranscriptionResult` 结构体，便于组件中类型安全地访问 `segments`

---

- [x] **Step 2: 实现 API 函数**

```typescript
import client from './client'

export async function createTranscription(
  file: File,
  options?: {
    language?: string;
    onProgress?: (percent: number) => void;
  }
): Promise<Transcription> {
  const formData = new FormData()
  formData.append('file', file)
  if (options?.language) {
    formData.append('language', options.language)
  }

  const { data } = await client.post('/v1/transcriptions', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (options?.onProgress && progressEvent.total) {
        const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        options.onProgress(percent)
      }
    },
  })
  return data
}

export async function listTranscriptions(
  params?: {
    page?: number;
    page_size?: number;
    status?: TranscriptionStatus;
  }
): Promise<TranscriptionListResponse> {
  const { data } = await client.get('/v1/transcriptions', { params })
  return data
}

export async function getTranscription(id: string): Promise<TranscriptionDetail> {
  const { data } = await client.get(`/v1/transcriptions/${id}`)
  return data
}

export async function downloadTranscription(
  id: string,
  format: 'json' | 'txt' | 'srt' | 'vtt' | 'zip'
): Promise<void> {
  const response = await client.get(`/v1/transcriptions/${id}/download`, {
    params: { format },
    responseType: 'blob',
  })

  const contentDisposition = response.headers['content-disposition']
  let filename = `${id}.${format}`
  if (contentDisposition) {
    const match = contentDisposition.match(/filename="?([^"]+)"?/)
    if (match) filename = match[1]
  }

  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function deleteTranscription(id: string): Promise<void> {
  await client.delete(`/v1/transcriptions/${id}`)
}
```

> **设计说明:**
> - `createTranscription` 使用 `FormData` 上传文件，`onUploadProgress` 提供进度回调给 UI
> - `downloadTranscription` 使用 `responseType: 'blob'` 接收二进制流，通过临时 `<a>` 标签触发浏览器下载
> - 从 `Content-Disposition` 头提取后端生成的文件名（基于原始文件名），fallback 使用 `id.format`
> - 所有函数复用已有的 `client.ts` axios 实例，自动处理 JWT 和 401 跳转

---

- [x] **Step 3: 补充后端 DELETE 路由**

```python
# backend/app/api/v1/transcription.py — 新增
import os

@router.delete("/{transcription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transcription(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除转录记录及其关联的音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    # 删除磁盘上的音频文件
    if os.path.exists(transcription.file_path):
        os.remove(transcription.file_path)

    await db.delete(transcription)
    await db.commit()
```

> **设计说明:**
> - 先删文件再删记录，避免记录删除后找不到文件路径
> - `user_id` 校验确保只能删除自己的记录
> - 返回 204 No Content，符合 REST 删除规范

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/api/transcription.ts backend/app/api/v1/transcription.py
git commit -m "feat(task11): add frontend transcription API module with upload/list/detail/download/delete"
```

---
