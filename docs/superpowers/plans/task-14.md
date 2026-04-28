# Task 14: 转录详情页 — 说话人分色 + 时间戳 + 下载

> 所属阶段: 阶段四：前端业务页面


**Goal:** 实现转录详情页面，从路由参数获取转录 ID，加载详情数据，展示音频播放器（completed 状态）、转录结果（复用 TranscriptionViewer）、返回按钮。支持从 Dashboard 和 History 页面跳转进入。

**Files:**
- Modify: `frontend/src/views/TranscriptionDetailView.vue`

- [x] **Step 1: 实现 TranscriptionDetailView.vue**

```vue
<!-- frontend/src/views/TranscriptionDetailView.vue -->
<template>
  <div class="space-y-6">
    <!-- 返回栏 + 标题 -->
    <div class="flex items-center gap-4">
      <button
        @click="goBack"
        class="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-lg transition-colors"
      >
        <span class="material-symbols-outlined">arrow_back</span>
      </button>
      <div class="min-w-0">
        <h2 class="text-xl font-semibold tracking-tight text-on-surface truncate">
          {{ transcription?.filename || '转录详情' }}
        </h2>
        <p v-if="statusText" class="text-sm text-on-surface-variant mt-0.5">{{ statusText }}</p>
      </div>
    </div>

    <!-- 音频播放器 -->
    <div
      v-if="transcription?.status === 'completed'"
      class="bg-surface-container-lowest rounded-xl p-4"
    >
      <audio :src="audioUrl" controls class="w-full" />
    </div>

    <!-- 转录结果 -->
    <TranscriptionViewer :transcription="transcription" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TranscriptionViewer from '@/components/TranscriptionViewer.vue'
import { getTranscription, type TranscriptionDetail } from '@/api/transcription'

const route = useRoute()
const router = useRouter()

const transcription = ref<TranscriptionDetail | null>(null)
const loading = ref(false)

const statusText = computed(() => {
  if (!transcription.value) return ''
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '转录中',
    completed: '已完成',
    failed: '转录失败',
  }
  return map[transcription.value.status] || ''
})

const audioUrl = computed(() => {
  if (!transcription.value) return ''
  return `/api/v1/transcriptions/${transcription.value.id}/audio`
})

onMounted(async () => {
  const id = route.params.id as string
  if (!id) {
    router.push({ name: 'history' })
    return
  }

  loading.value = true
  try {
    const data = await getTranscription(id)
    transcription.value = data
  } catch {
    alert('加载转录详情失败')
    router.push({ name: 'history' })
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.back()
}
</script>
```

> **设计说明:**
> - 复用 `TranscriptionViewer` 组件展示转录结果，保持 Dashboard 和详情页展示一致性
> - 音频播放器仅 completed 状态显示，使用原生 `<audio>` 标签
> - 返回按钮使用 `router.back()`，兼容从 Dashboard 或 History 页面进入的场景
> - 加载失败自动跳转到历史记录页，避免用户停留在错误状态
> - 页面标题显示原始文件名，下方小字显示状态

---

- [x] **Step 2: 提交**

```bash
git add frontend/src/views/TranscriptionDetailView.vue
git commit -m "feat(task14): add Transcription Detail page with audio player and back navigation"
```

> **设计说明:**
> - 详情页无独立组件拆分，直接复用 TranscriptionViewer 保持代码复用
> - 音频播放地址复用 Task 13 新增的 `/audio` 端点
> - 路由参数 `/:id` 已在 Task 9 的 router 中定义，无需修改

---

## 阶段五：集成与收尾
