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