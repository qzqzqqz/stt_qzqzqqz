# Task 9: Vue3 脚手架 + 设计系统 + 路由 + 状态管理

> 所属阶段: 阶段三：前端基础


**Goal:** 从零搭建 Vue3 SPA 前端项目，集成 Vite + TypeScript + Tailwind CSS + Vue Router + Pinia，配置 "The Sonic Gallery" 设计系统，建立基础目录结构和布局框架。

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`, `tsconfig.app.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.ts`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/assets/main.css`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/stores/auth.ts`, `stores/app.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/components/AppLayout.vue`, `AppSidebar.vue`, `AppTopbar.vue`
- Create: `frontend/src/views/LoginView.vue`, `RegisterView.vue`, `DashboardView.vue`, `HistoryView.vue`, `TranscriptionDetailView.vue`

- [x] **Step 1: 初始化 Vue3 + Vite 项目**

```bash
cd /Users/qizhao/project_git/stt_qzqzqqz
npm create vite@latest frontend -- --template vue-ts
```

选择 Vue + TypeScript，这会生成 `frontend/` 目录和基础文件结构。

- [x] **Step 2: 安装依赖**

```bash
cd frontend
npm install
npm install vue-router@4 pinia axios
npm install -D tailwindcss @tailwindcss/vite
```

- [x] **Step 3: 配置 Tailwind CSS（The Sonic Gallery 设计系统）**

创建 `frontend/tailwind.config.ts`：

```typescript
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: '#0053db',
        'primary-dim': '#0048c1',
        surface: '#f7f9fb',
        'surface-container-low': '#f0f4f7',
        'surface-container': '#e8eff3',
        'surface-container-high': '#d9e4ea',
        'surface-container-highest': '#d9e4ea',
        'on-surface': '#2a3439',
        'on-surface-variant': '#566166',
        'outline-variant': '#a9b4b9',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        ambient: '0 12px 40px rgba(42, 52, 57, 0.06)',
      },
      borderRadius: {
        md: '0.75rem',
      },
    },
  },
  plugins: [],
} satisfies Config
```

创建 `frontend/src/assets/main.css`：

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import 'tailwindcss';

@theme {
  --color-primary: #0053db;
  --color-primary-dim: #0048c1;
  --color-surface: #f7f9fb;
  --color-surface-container-low: #f0f4f7;
  --color-surface-container: #e8eff3;
  --color-surface-container-high: #d9e4ea;
  --color-surface-container-highest: #d9e4ea;
  --color-on-surface: #2a3439;
  --color-on-surface-variant: #566166;
  --color-outline-variant: #a9b4b9;
  --font-sans: 'Inter', system-ui, sans-serif;
}

body {
  @apply bg-surface text-on-surface font-sans antialiased;
}
```

> **设计说明:**
> - 颜色系统遵循 "The Sonic Gallery" 规范：信号蓝 `#0053db` 为主色，表面灰 `#f7f9fb` 为背景
> - 无边框原则：用背景色差分层，禁用 1px solid 边框做区域划分
> - 环境阴影使用 `rgba(42,52,57,0.06)`，不用纯黑

- [x] **Step 4: 配置 Vite 和路径别名**

更新 `frontend/vite.config.ts`：

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

更新 `frontend/tsconfig.app.json` 添加路径别名：

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

> **设计说明:**
> - Vite dev server 代理 `/api` 到后端 `localhost:8000`，开发环境直接联调
> - 路径别名 `@/` 指向 `src/`，避免相对路径 `../../../` 地狱

- [x] **Step 5: 配置 Vue Router + 路由守卫**

创建 `frontend/src/router/index.ts`：

```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/components/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'history',
          name: 'history',
          component: () => import('@/views/HistoryView.vue'),
        },
        {
          path: 'transcriptions/:id',
          name: 'transcription-detail',
          component: () => import('@/views/TranscriptionDetailView.vue'),
        },
      ],
    },
  ],
})

router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem('access_token')
  if (!to.meta.public && !isAuthenticated) {
    next({ name: 'login' })
  } else {
    next()
  }
})

export default router
```

> **设计说明:**
> - 登录/注册页标记 `meta: { public: true }`，路由守卫放行
> - 未登录用户访问受保护路由自动跳转 `/login`
> - 布局路由使用 `AppLayout.vue` 作为父级，子路由嵌套在内容区

- [x] **Step 6: 配置 Pinia 状态管理**

创建 `frontend/src/stores/auth.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface User {
  id: string
  email: string
  real_name: string
  department: string
  phone: string | null
  is_active: boolean
  created_at: string
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const user = ref<User | null>(null)

  const isAuthenticated = computed(() => !!accessToken.value)

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearAuth() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  function setUser(userData: User) {
    user.value = userData
  }

  return {
    accessToken, refreshToken, user,
    isAuthenticated, setTokens, clearAuth, setUser,
  }
})
```

创建 `frontend/src/stores/app.ts`：

```typescript
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const isLoading = ref(false)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  return { sidebarCollapsed, isLoading, toggleSidebar }
})
```

- [x] **Step 7: 创建 API 客户端**

创建 `frontend/src/api/client.ts`：

```typescript
import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
```

> **设计说明:**
> - 请求拦截器自动附加 JWT token，无需每个 API 调用手动传 token
> - 响应拦截器统一处理 401：清除 token 并跳转登录页

- [x] **Step 8: 创建布局组件**

创建 `frontend/src/components/AppLayout.vue`：

```vue
<template>
  <div class="flex h-screen bg-surface">
    <AppSidebar />
    <div class="flex-1 flex flex-col min-w-0">
      <AppTopbar />
      <main class="flex-1 overflow-auto p-6">
        <div class="max-w-7xl mx-auto">
          <RouterView />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppSidebar from './AppSidebar.vue'
import AppTopbar from './AppTopbar.vue'
</script>
```

创建 `frontend/src/components/AppSidebar.vue`：

```vue
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
```

创建 `frontend/src/components/AppTopbar.vue`：

```vue
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
```

> **设计说明:**
> - 侧边栏和顶部栏均使用毛玻璃效果 `backdrop-blur-xl` + 半透明背景
> - 左侧栏固定宽 64，主内容区 `max-w-7xl` 居中，适配大屏
> - 导航当前项使用主色背景，非当前项 hover 显示 `surface-container-low`

- [x] **Step 9: 创建页面占位组件**

创建 5 个空壳页面（后续 Task 10-13 填充内容）：

```vue
<!-- frontend/src/views/LoginView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <h2 class="text-headline-sm font-semibold">登录</h2>
    <p class="text-on-surface-variant mt-2">开发中...</p>
  </div>
</template>
```

同理创建 `RegisterView.vue`、`DashboardView.vue`、`HistoryView.vue`、`TranscriptionDetailView.vue`。

- [x] **Step 10: 配置应用入口**

更新 `frontend/src/main.ts`：

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
```

更新 `frontend/src/App.vue`：

```vue
<template>
  <RouterView />
</template>
```

更新 `frontend/index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0" />
    <title>STT 音频转录</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [x] **Step 11: 验证启动**

```bash
cd frontend
npm run dev
```

验证：
- `http://localhost:5173/login` 显示登录页占位
- `http://localhost:5173/` 因未登录自动跳转 `/login`
- localStorage 中手动设置 `access_token=test` 后刷新 `/` 显示布局框架

- [x] **Step 12: 提交**

```bash
git add frontend/
git commit -m "feat(task9): scaffold Vue3 frontend with Vite, Tailwind, Router, Pinia"
```

---
