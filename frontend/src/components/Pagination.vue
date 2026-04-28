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
