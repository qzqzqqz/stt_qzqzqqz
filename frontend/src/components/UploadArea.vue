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