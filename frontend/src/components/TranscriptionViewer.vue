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
import InfoRow from './InfoRow.vue'
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