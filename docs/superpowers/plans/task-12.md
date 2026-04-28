# Task 12: 转录工作台 Dashboard — 上传区 + 进度条 + 结果展示

> 所属阶段: 阶段四：前端业务页面


**Goal:** 实现 Dashboard 页面，包含音频上传区（拖拽+点击）、转录状态可视化、转录结果展示（说话人+时间戳）、音频属性面板、多格式下载按钮组。支持上传后自动轮询状态，URL 同步 transcription ID，刷新不丢失当前任务。

**Files:**
- Modify: `frontend/src/views/DashboardView.vue` — 主页面容器
- Create: `frontend/src/components/UploadArea.vue` — 拖拽/点击上传组件
- Create: `frontend/src/components/TranscriptionViewer.vue` — 转录结果展示组件

- [x] **Step 1: 创建 UploadArea 组件**

```vue
<!-- frontend/src/components/UploadArea.vue -->
<template>
  <div class="space-y-4">
    <!-- 拖拽上传区 -->
    <div
      class="relative rounded-xl p-10 text-center transition-all duration-200 cursor-pointer"
      :class="[
        isDragging
          ? 'bg-primary/5 ring-2 ring-primary/30'
          : 'bg-surface-container-low hover:bg-surface-container',
      ]"
      @dragenter.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        ref="fileInput"
        type="file"
        class="hidden"
        accept=".wav,.mp3,.flac,.m4a,.ogg"
        @change="handleFileSelect"
      />
      <span
        class="material-symbols-outlined text-4xl mb-3"
        :class="isDragging ? 'text-primary' : 'text-on-surface-variant'"
      >
        upload_file
      </span>
      <p class="text-sm text-on-surface font-medium">
        {{ isDragging ? '松开以上传音频文件' : '拖拽音频文件到此处，或点击选择' }}
      </p>
      <p class="text-xs text-on-surface-variant mt-2">
        支持 WAV、MP3、FLAC、M4A、OGG，最大 500MB
      </p>
    </div>

    <!-- 已选文件 + 上传按钮 -->
    <div
      v-if="selectedFile"
      class="flex items-center justify-between bg-surface-container-lowest rounded-xl p-4"
    >
      <div class="flex items-center gap-3 min-w-0">
        <span class="material-symbols-outlined text-on-surface-variant">audio_file</span>
        <div class="min-w-0">
          <p class="text-sm font-medium text-on-surface truncate">{{ selectedFile.name }}</p>
          <p class="text-xs text-on-surface-variant">{{ formatFileSize(selectedFile.size) }}</p>
        </div>
      </div>

      <div class="flex items-center gap-3">
        <div v-if="isUploading" class="w-32">
          <div class="h-1.5 bg-surface-container-high rounded-full overflow-hidden">
            <div
              class="h-full bg-primary rounded-full transition-all duration-300"
              :style="{ width: `${uploadProgress}%` }"
            />
          </div>
          <p class="text-xs text-on-surface-variant mt-1 text-right">{{ uploadProgress }}%</p>
        </div>

        <button
          v-else
          @click.stop="handleUpload"
          class="px-5 py-2 bg-gradient-to-br from-primary to-primary-dim text-white text-sm font-medium rounded-lg hover:shadow-lg hover:shadow-primary/20 transition-all active:scale-[0.98]"
        >
          开始转录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{
  upload: [file: File]
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const selectedFile = ref<File | null>(null)
const isUploading = ref(false)
const uploadProgress = ref(0)

const MAX_SIZE_MB = 500

function triggerFileInput() {
  fileInput.value?.click()
}

function handleFileSelect(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files?.[0]) validateAndSetFile(input.files[0])
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const file = e.dataTransfer?.files[0]
  if (file) validateAndSetFile(file)
}

function validateAndSetFile(file: File) {
  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    alert(`文件过大，最大支持 ${MAX_SIZE_MB}MB`)
    return
  }
  selectedFile.value = file
  isUploading.value = false
  uploadProgress.value = 0
}

function handleUpload() {
  if (!selectedFile.value) return
  isUploading.value = true
  emit('upload', selectedFile.value)
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function reset() {
  selectedFile.value = null
  isUploading.value = false
  uploadProgress.value = 0
  if (fileInput.value) fileInput.value.value = ''
}

function setProgress(p: number) {
  uploadProgress.value = p
}

defineExpose({ reset, setProgress })
</script>
```

> **设计说明:**
> - 拖拽区用 `bg-surface-container-low`，hover 加深到 `bg-surface-container`，不用边框
> - 拖拽进入时用 `ring-2 ring-primary/30` 提供视觉反馈
> - 上传进度条使用 `surface-container-high` 背景 + `primary` 填充
> - 暴露 `reset()` 和 `setProgress()` 方法供父组件控制

---

- [x] **Step 2: 创建 TranscriptionViewer 组件**

```vue
<!-- frontend/src/components/TranscriptionViewer.vue -->
<template>
  <div v-if="transcription" class="space-y-6 mt-8">
    <!-- 状态指示器 -->
    <div class="flex items-center gap-3 px-5 py-3 rounded-xl" :class="statusBgClass">
      <span class="material-symbols-outlined">{{ statusIcon }}</span>
      <span class="text-sm font-medium">{{ statusText }}</span>
      <span v-if="transcription.error_message" class="text-xs text-red-600 ml-2">
        {{ transcription.error_message }}
      </span>
    </div>

    <!-- 两栏布局：左侧属性面板 + 右侧 Segments -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <!-- 音频属性面板 -->
      <div class="lg:col-span-1 space-y-4">
        <div class="bg-surface-container-lowest rounded-xl p-5 space-y-4">
          <h3 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant">
            音频属性
          </h3>
          <div class="space-y-3">
            <InfoRow label="文件名" :value="transcription.filename" />
            <InfoRow label="文件大小" :value="formatFileSize(transcription.file_size)" />
            <InfoRow label="音频时长" :value="formatDuration(transcription.duration)" />
            <InfoRow label="检测语言" :value="transcription.language || '自动检测'" />
            <InfoRow label="转录模型" :value="transcription.model_used" />
            <InfoRow label="创建时间" :value="formatDate(transcription.created_at)" />
            <InfoRow
              v-if="transcription.completed_at"
              label="完成时间"
              :value="formatDate(transcription.completed_at)"
            />
          </div>
        </div>

        <!-- 下载按钮组（仅 completed） -->
        <div v-if="transcription.status === TranscriptionStatus.completed" class="space-y-2">
          <h3 class="text-xs font-bold uppercase tracking-wider text-on-surface-variant px-1">
            导出结果
          </h3>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="fmt in downloadFormats"
              :key="fmt"
              @click="handleDownload(fmt)"
              class="px-3 py-2 bg-surface-container-low hover:bg-surface-container text-xs font-medium text-on-surface rounded-lg transition-colors text-center"
            >
              {{ fmt.toUpperCase() }}
            </button>
          </div>
        </div>
      </div>

      <!-- Segments 列表 -->
      <div class="lg:col-span-3">
        <div
          v-if="transcription.status === TranscriptionStatus.completed && segments.length > 0"
          class="bg-surface-container-lowest rounded-xl p-6 space-y-6"
        >
          <div v-for="(seg, idx) in segments" :key="idx" class="group">
            <div class="flex items-start gap-4">
              <div class="shrink-0 pt-0.5">
                <span class="inline-block px-2 py-1 bg-surface-container-low text-xs font-mono text-on-surface-variant rounded-md">
                  {{ formatTime(seg.start) }} - {{ formatTime(seg.end) }}
                </span>
              </div>
              <div class="shrink-0">
                <span
                  class="inline-block px-3 py-1 text-xs font-medium rounded-full"
                  :class="speakerColorClass(seg.speaker)"
                >
                  {{ seg.speaker }}
                </span>
              </div>
              <p class="text-sm text-on-surface leading-relaxed flex-1">{{ seg.text }}</p>
            </div>
          </div>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.completed && transcription.result_text"
          class="bg-surface-container-lowest rounded-xl p-6"
        >
          <p class="text-sm text-on-surface leading-relaxed whitespace-pre-wrap">
            {{ transcription.result_text }}
          </p>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.processing"
          class="bg-surface-container-lowest rounded-xl p-12 flex flex-col items-center justify-center"
        >
          <div class="w-10 h-10 border-3 border-surface-container-high border-t-primary rounded-full animate-spin mb-4" />
          <p class="text-sm text-on-surface-variant">正在转录中，请稍候...</p>
        </div>

        <div
          v-else-if="transcription.status === TranscriptionStatus.pending"
          class="bg-surface-container-lowest rounded-xl p-12 flex flex-col items-center justify-center"
        >
          <span class="material-symbols-outlined text-3xl text-on-surface-variant mb-3">schedule</span>
          <p class="text-sm text-on-surface-variant">任务已加入队列，等待处理...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  TranscriptionStatus,
  type TranscriptionDetail,
  downloadTranscription,
} from '@/api/transcription'

const props = defineProps<{
  transcription: TranscriptionDetail | null
}>()

const downloadFormats = ['json', 'txt', 'srt', 'vtt', 'zip'] as const

const statusText = computed(() => {
  const map: Record<string, string> = {
    pending: '等待处理',
    processing: '转录中',
    completed: '已完成',
    failed: '转录失败',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const statusIcon = computed(() => {
  const map: Record<string, string> = {
    pending: 'schedule',
    processing: 'autorenew',
    completed: 'check_circle',
    failed: 'error',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const statusBgClass = computed(() => {
  const map: Record<string, string> = {
    pending: 'bg-surface-container-low text-on-surface-variant',
    processing: 'bg-primary/5 text-primary',
    completed: 'bg-green-50 text-green-700',
    failed: 'bg-red-50 text-red-700',
  }
  return props.transcription ? map[props.transcription.status] : ''
})

const segments = computed(() => {
  if (!props.transcription?.result_json?.segments) return []
  return props.transcription.result_json.segments.map((seg) => ({
    start: seg.start_time,
    end: seg.end_time,
    speaker: `Speaker ${seg.speaker_id}`,
    text: seg.text,
  }))
})

const speakerColors: Record<string, string> = {
  'Speaker 0': 'bg-blue-50 text-blue-700',
  'Speaker 1': 'bg-purple-50 text-purple-700',
  'Speaker 2': 'bg-amber-50 text-amber-700',
  'Speaker 3': 'bg-emerald-50 text-emerald-700',
}

function speakerColorClass(speaker: string): string {
  return speakerColors[speaker] || 'bg-surface-container text-on-surface-variant'
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function formatDuration(seconds: number | null): string {
  if (!seconds) return '—'
  return formatTime(seconds)
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('zh-CN')
}

async function handleDownload(format: string) {
  if (!props.transcription) return
  await downloadTranscription(
    props.transcription.id,
    format as 'json' | 'txt' | 'srt' | 'vtt' | 'zip'
  )
}
</script>
```

> **设计说明:**
> - 两栏布局：左侧 1/4 属性面板 + 下载按钮，右侧 3/4 转录内容
> - 说话人分色使用浅背景 + 深色文字（blue/purple/amber/emerald），确保可读性
> - 时间戳用等宽字体 + `surface-container-low` 背景标签
> - 状态指示器用背景色区分：processing 用 primary/5，completed 用 green-50，failed 用 red-50
> - 无 segment 数据时 fallback 展示纯文本结果

---

- [x] **Step 3: 实现 DashboardView 页面**

```vue
<!-- frontend/src/views/DashboardView.vue -->
<template>
  <div class="space-y-6">
    <div>
      <h2 class="text-headline-sm font-semibold tracking-tight">转录工作台</h2>
      <p class="text-sm text-on-surface-variant mt-1">
        上传音频文件，系统将自动进行带说话人分离和时间戳的转录
      </p>
    </div>

    <UploadArea ref="uploadAreaRef" @upload="handleUpload" />
    <TranscriptionViewer :transcription="currentTranscription" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UploadArea from '@/components/UploadArea.vue'
import TranscriptionViewer from '@/components/TranscriptionViewer.vue'
import {
  createTranscription,
  getTranscription,
  type TranscriptionDetail,
} from '@/api/transcription'

const route = useRoute()
const router = useRouter()
const uploadAreaRef = ref<InstanceType<typeof UploadArea> | null>(null)

const currentTranscription = ref<TranscriptionDetail | null>(null)
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)

async function handleUpload(file: File) {
  try {
    const transcription = await createTranscription(file, {
      onProgress: (percent) => uploadAreaRef.value?.setProgress(percent),
    })
    currentTranscription.value = transcription as TranscriptionDetail
    uploadAreaRef.value?.reset()
    router.replace({ query: { t: transcription.id } })

    if (transcription.status !== 'completed' && transcription.status !== 'failed') {
      startPolling(transcription.id)
    }
  } catch (err: any) {
    alert(err.response?.data?.detail || '上传失败，请重试')
    uploadAreaRef.value?.reset()
  }
}

function startPolling(id: string) {
  stopPolling()
  pollTimer.value = setInterval(async () => {
    try {
      const data = await getTranscription(id)
      currentTranscription.value = data
      if (data.status === 'completed' || data.status === 'failed') {
        stopPolling()
      }
    } catch {
      stopPolling()
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer.value) {
    clearInterval(pollTimer.value)
    pollTimer.value = null
  }
}

onMounted(async () => {
  const id = route.query.t as string | undefined
  if (id) {
    try {
      const data = await getTranscription(id)
      currentTranscription.value = data
      if (data.status !== 'completed' && data.status !== 'failed') {
        startPolling(id)
      }
    } catch {
      router.replace({ query: {} })
    }
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>
```

> **设计说明:**
> - URL 同步：上传成功后更新 `?t=xxx`，刷新页面自动加载该转录并继续轮询
> - 轮询间隔 3 秒，completed/failed 时自动停止
> - 上传进度通过组件 ref 的 `setProgress` 回传，完成后 `reset()` 清空上传区
> - 页面加载时检查 URL 参数，无效 ID 自动清除参数

---

- [x] **Step 4: 提交**

```bash
git add frontend/src/views/DashboardView.vue \
    frontend/src/components/UploadArea.vue \
    frontend/src/components/TranscriptionViewer.vue
git commit -m "feat(task12): add Dashboard with upload area, status polling, and transcription viewer"
```

> **关键设计决策:**
> - URL 同步 `?t=`：刷新不丢失当前转录任务
> - 轮询 3s 间隔：平衡实时性和服务端压力
> - 组件 ref 控制上传区：`reset()` + `setProgress()` 精确控制
> - 说话人 4 色循环：超过 4 个 fallback 灰色
> - 两栏 1:3 布局：大屏侧栏固定，小屏堆叠

---
