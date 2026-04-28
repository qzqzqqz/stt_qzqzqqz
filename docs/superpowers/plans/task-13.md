# Task 13: 历史记录页 — 列表 + 搜索筛选 + 分页

> 所属阶段: 阶段四：前端业务页面


**Goal:** 实现历史记录页面，支持按文件名搜索、按状态筛选、分页展示转录任务列表。每条记录展示文件名、创建时间、时长、状态和操作按钮（查看详情、下载结果、下载原始音频、删除）。同步补充后端搜索参数和原始音频下载端点。

**Files:**
- Create: `frontend/src/components/Pagination.vue` — 分页组件
- Modify: `frontend/src/views/HistoryView.vue` — 历史记录列表页
- Modify: `backend/app/api/v1/transcription.py` — 添加 search 参数和 `/audio` 端点

- [x] **Step 1: 创建 Pagination 组件**

```vue
<!-- frontend/src/components/Pagination.vue -->
<template>
  <div class="flex items-center justify-between">
    <p class="text-xs text-on-surface-variant">
      共 {{ totalItems }} 条，{{ totalPages }} 页
    </p>
    <div class="flex items-center gap-1">
      <button
        :disabled="currentPage <= 1"
        @click="$emit('update:page', currentPage - 1)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <span class="material-symbols-outlined text-sm">chevron_left</span>
      </button>

      <button
        v-for="page in visiblePages"
        :key="page"
        @click="$emit('update:page', page)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm font-medium transition-colors"
        :class="page === currentPage ? 'bg-primary text-white' : 'text-on-surface hover:bg-surface-container-low'"
      >
        {{ page }}
      </button>

      <button
        :disabled="currentPage >= totalPages"
        @click="$emit('update:page', currentPage + 1)"
        class="w-8 h-8 flex items-center justify-center rounded-lg text-sm text-on-surface-variant hover:bg-surface-container-low disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <span class="material-symbols-outlined text-sm">chevron_right</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  currentPage: number
  totalPages: number
  totalItems: number
}>()

defineEmits<{
  'update:page': [page: number]
}>()

const visiblePages = computed(() => {
  const pages: number[] = []
  const maxVisible = 5
  let start = Math.max(1, props.currentPage - Math.floor(maxVisible / 2))
  let end = Math.min(props.totalPages, start + maxVisible - 1)
  if (end - start + 1 < maxVisible) {
    start = Math.max(1, end - maxVisible + 1)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})
</script>
```

> **设计说明:**
> - 当前页用 `bg-primary text-white` 高亮，其他页 hover 加深背景
> - 最多显示 5 个页码，自动滑动保持当前页居中
> - 上一页/下一页在边界时 disabled

---

- [x] **Step 2: 修改后端 API（搜索 + 原始音频下载）**

```python
# backend/app/api/v1/transcription.py

# 1. 在导入区添加 FileResponse
from fastapi.responses import FileResponse, StreamingResponse

# 2. 在 list_transcriptions 中添加 search 参数
@router.get("/", response_model=TranscriptionListResponse)
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: TranscriptionStatus | None = Query(None),
    search: str | None = Query(None, description="按文件名搜索"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Transcription).where(Transcription.user_id == current_user.id)
    count_query = select(func.count()).select_from(Transcription).where(Transcription.user_id == current_user.id)

    if status:
        query = query.where(Transcription.status == status)
        count_query = count_query.where(Transcription.status == status)

    if search:
        query = query.where(Transcription.filename.ilike(f"%{search}%"))
        count_query = count_query.where(Transcription.filename.ilike(f"%{search}%"))

    query = query.order_by(Transcription.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar()
    pages = (total + page_size - 1) // page_size

    return TranscriptionListResponse(
        items=list(items), total=total, page=page, page_size=page_size, pages=pages,
    )

# 3. 添加原始音频下载端点（放在文件末尾）
@router.get("/{transcription_id}/audio")
async def download_audio(
    transcription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载原始音频文件."""
    result = await db.execute(
        select(Transcription).where(
            Transcription.id == transcription_id,
            Transcription.user_id == current_user.id,
        )
    )
    transcription = result.scalar_one_or_none()

    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    if not os.path.exists(transcription.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(
        transcription.file_path,
        filename=transcription.filename,
        media_type="application/octet-stream",
    )
```

> **设计说明:**
> - `search` 参数使用 `ilike` 实现不区分大小写的模糊匹配
> - 原始音频下载使用 `FileResponse`，由 FastAPI 自动处理大文件流式传输
> - `media_type="application/octet-stream"` 强制浏览器下载而非预览

---

- [x] **Step 3: 实现 HistoryView 页面**

```vue
<!-- frontend/src/views/HistoryView.vue -->
<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-on-surface">历史记录</h2>
      <p class="text-sm text-on-surface-variant mt-1">查看和管理您的所有转录任务</p>
    </div>

    <!-- 搜索 + 状态筛选 -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-sm">search</span>
        <input
          v-model="searchQuery"
          @input="handleSearch"
          type="text"
          placeholder="搜索文件名..."
          class="w-full pl-10 pr-4 py-2.5 bg-surface-container-lowest rounded-lg text-sm text-on-surface placeholder:text-on-surface-variant focus:outline-none focus:ring-2 focus:ring-primary/20"
        />
      </div>
      <div class="flex gap-2">
        <button
          v-for="s in statusOptions"
          :key="s.value"
          @click="handleStatusChange(s.value)"
          class="px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap"
          :class="currentStatus === s.value ? 'bg-primary text-white' : 'bg-surface-container-low text-on-surface-variant hover:bg-surface-container'"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- 列表 -->
    <div class="space-y-2">
      <!-- 表头 -->
      <div class="hidden sm:grid sm:grid-cols-12 px-4 py-2">
        <span class="col-span-5 text-xs font-bold uppercase tracking-wider text-on-surface-variant">文件名</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant">创建时间</span>
        <span class="col-span-1 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-right">时长</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-center">状态</span>
        <span class="col-span-2 text-xs font-bold uppercase tracking-wider text-on-surface-variant text-right">操作</span>
      </div>

      <!-- 列表项 -->
      <div
        v-for="item in items"
        :key="item.id"
        class="bg-surface-container-lowest rounded-xl p-4 flex flex-col sm:grid sm:grid-cols-12 sm:items-center gap-3 sm:gap-4 hover:bg-surface-container-low transition-colors"
      >
        <!-- 文件名 -->
        <div class="sm:col-span-5 flex items-center gap-3 min-w-0">
          <div class="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center shrink-0">
            <span class="material-symbols-outlined text-on-surface-variant text-lg">audio_file</span>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium text-on-surface truncate">{{ item.filename }}</p>
            <p class="text-xs text-on-surface-variant">{{ formatFileSize(item.file_size) }}</p>
          </div>
        </div>

        <!-- 创建时间 -->
        <div class="sm:col-span-2 text-sm text-on-surface-variant">{{ formatDate(item.created_at) }}</div>

        <!-- 时长 -->
        <div class="sm:col-span-1 text-sm text-on-surface-variant text-right">{{ formatDuration(item.duration) }}</div>

        <!-- 状态 -->
        <div class="sm:col-span-2 flex justify-center">
          <span
            class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium"
            :class="statusTagClass(item.status)"
          >
            <span v-if="item.status === 'processing'" class="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />
            {{ statusLabel(item.status) }}
          </span>
        </div>

        <!-- 操作 -->
        <div class="sm:col-span-2 flex items-center justify-end gap-1">
          <button
            @click="viewDetail(item.id)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="查看详情"
          >
            <span class="material-symbols-outlined text-sm">visibility</span>
          </button>
          <button
            @click="downloadResult(item.id)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="下载结果"
          >
            <span class="material-symbols-outlined text-sm">description</span>
          </button>
          <button
            @click="downloadAudio(item.id, item.filename)"
            class="p-1.5 text-on-surface-variant hover:text-primary hover:bg-primary/5 rounded-md transition-colors"
            title="下载原始音频"
          >
            <span class="material-symbols-outlined text-sm">music_note</span>
          </button>
          <button
            @click="confirmDelete(item)"
            class="p-1.5 text-on-surface-variant hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
            title="删除"
          >
            <span class="material-symbols-outlined text-sm">delete</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="items.length === 0" class="py-16 text-center">
      <span class="material-symbols-outlined text-4xl text-on-surface-variant mb-3">history</span>
      <p class="text-sm text-on-surface-variant">暂无转录记录</p>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pt-2">
      <Pagination
        :current-page="currentPage"
        :total-pages="totalPages"
        :total-items="totalItems"
        @update:page="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Pagination from '@/components/Pagination.vue'
import {
  listTranscriptions,
  deleteTranscription,
  downloadTranscription,
  TranscriptionStatus,
  type Transcription,
} from '@/api/transcription'

const router = useRouter()

const items = ref<Transcription[]>([])
const currentPage = ref(1)
const totalPages = ref(0)
const totalItems = ref(0)
const currentStatus = ref<string>('')
const searchQuery = ref('')
const searchTimer = ref<ReturnType<typeof setTimeout> | null>(null)

const statusOptions = [
  { value: '', label: '全部' },
  { value: TranscriptionStatus.pending, label: '等待中' },
  { value: TranscriptionStatus.processing, label: '转录中' },
  { value: TranscriptionStatus.completed, label: '已完成' },
  { value: TranscriptionStatus.failed, label: '失败' },
]

onMounted(() => {
  loadData()
})

async function loadData() {
  try {
    const params: Record<string, any> = { page: currentPage.value, page_size: 10 }
    if (currentStatus.value) params.status = currentStatus.value
    if (searchQuery.value) params.search = searchQuery.value
    const data = await listTranscriptions(params)
    items.value = data.items
    totalPages.value = data.pages
    totalItems.value = data.total
  } catch {
    alert('加载失败，请重试')
  }
}

function handlePageChange(page: number) {
  currentPage.value = page
  loadData()
}

function handleStatusChange(status: string) {
  currentStatus.value = status
  currentPage.value = 1
  loadData()
}

function handleSearch() {
  if (searchTimer.value) clearTimeout(searchTimer.value)
  searchTimer.value = setTimeout(() => {
    currentPage.value = 1
    loadData()
  }, 300)
}

function viewDetail(id: string) {
  router.push({ name: 'transcription-detail', params: { id } })
}

function downloadResult(id: string) {
  downloadTranscription(id, 'zip')
}

function downloadAudio(id: string, filename: string) {
  const link = document.createElement('a')
  link.href = `/api/v1/transcriptions/${id}/audio`
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
}

async function confirmDelete(item: Transcription) {
  if (!confirm(`确定要删除 "${item.filename}" 吗？此操作不可恢复。`)) return
  try {
    await deleteTranscription(item.id)
    loadData()
  } catch {
    alert('删除失败')
  }
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN')
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '等待中',
    processing: '转录中',
    completed: '已完成',
    failed: '失败',
  }
  return map[status] || status
}

function statusTagClass(status: string): string {
  const map: Record<string, string> = {
    pending: 'bg-slate-100 text-slate-600',
    processing: 'bg-blue-50 text-blue-700',
    completed: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
  }
  return map[status] || 'bg-surface-container text-on-surface-variant'
}
</script>
```

> **设计说明:**
> - 列表采用卡片形式（`bg-surface-container-lowest rounded-xl`），行之间用 `gap-2` 分隔，无 1px 边框
> - 响应式：小屏时堆叠显示，大屏时用 `grid-cols-12` 对齐列
> - 搜索 300ms debounce，减少不必要的 API 请求
> - 状态切换和页码切换时重置到第一页
> - 操作按钮使用图标 + title，hover 时显示主色/红色反馈
> - 空状态居中展示，带图标和提示文字

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/components/Pagination.vue \
    frontend/src/views/HistoryView.vue \
    backend/app/api/v1/transcription.py
git commit -m "feat(task13): add History page with search, status filter, pagination, and audio download"
```

> **关键设计决策:**
> - 后端搜索用 `ilike` 模糊匹配，避免前端分页+搜索的数据不完整问题
> - 原始音频下载用 `FileResponse` 流式传输，避免大文件内存占用
> - 卡片列表替代传统表格，遵循设计系统"无边框"原则
> - 操作按钮图标化，节省空间，title 提供可访问性提示

---
