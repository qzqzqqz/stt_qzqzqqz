<template>
  <aside class="w-64 h-screen fixed left-0 top-0 z-50 flex flex-col">
    <div class="h-full bg-surface/80 backdrop-blur-xl border-r border-outline-variant/20 flex flex-col">
      <div class="h-16 flex items-center px-6">
        <span class="text-xl font-semibold text-primary">STT</span>
      </div>
      <nav class="flex-1 px-4 py-4 space-y-1">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 px-4 py-3 rounded-md text-sm font-medium transition-colors"
          :class="route.path === item.path ? 'bg-primary text-white' : 'text-on-surface-variant hover:bg-surface-container-low'"
        >
          <span class="material-symbols-outlined text-lg">{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="p-4 border-t border-outline-variant/20">
        <button
          @click="logout"
          class="flex items-center gap-3 px-4 py-3 w-full rounded-md text-sm text-on-surface-variant hover:bg-surface-container-low transition-colors"
        >
          <span class="material-symbols-outlined text-lg">logout</span>
          退出登录
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const navItems = [
  { path: '/', label: '仪表盘', icon: 'dashboard' },
  { path: '/history', label: '历史记录', icon: 'history' },
]

function logout() {
  authStore.clearAuth()
  router.push({ name: 'login' })
}
</script>