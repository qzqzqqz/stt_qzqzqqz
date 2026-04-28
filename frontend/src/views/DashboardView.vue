<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div>
      <h2 class="text-2xl font-semibold tracking-tight text-on-surface">转录工作台</h2>
      <p class="text-sm text-on-surface-variant mt-1">
        上传音频文件，系统将自动进行带说话人分离和时间戳的转录
      </p>
    </div>

    <!-- 上传区 -->
    <UploadArea ref="uploadAreaRef" @upload="handleUpload" />

    <!-- 转录结果 -->
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

// ── 上传处理 ──
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

// ── 轮询 ──
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

// ── 页面加载时检查 URL 参数 ──
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