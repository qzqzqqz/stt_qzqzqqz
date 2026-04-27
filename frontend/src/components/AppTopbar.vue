<template>
  <header class="h-16 bg-surface/80 backdrop-blur-xl border-b border-outline-variant/20 flex items-center justify-between px-6 sticky top-0 z-40">
    <h1 class="text-headline-sm font-semibold tracking-tight">{{ pageTitle }}</h1>
    <div class="flex items-center gap-4">
      <span class="text-sm text-on-surface-variant">{{ authStore.user?.real_name }}</span>
      <div class="w-8 h-8 rounded-full bg-primary text-white flex items-center justify-center text-sm font-medium">
        {{ authStore.user?.real_name?.[0] || '?' }}
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const authStore = useAuthStore()

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    dashboard: '转录工作台',
    history: '历史记录',
    'transcription-detail': '转录详情',
  }
  return titles[route.name as string] || ''
})
</script>