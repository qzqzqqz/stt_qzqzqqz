# Task 10: API 客户端 + Auth 逻辑（登录/注册页）

> 所属阶段: 阶段三：前端基础


**Goal:** 实现前端认证 API 模块，完成登录/注册页面，与后端 JWT 认证系统对接。

**Files:**
- Create: `frontend/src/api/auth.ts` — 认证相关 API 封装
- Modify: `frontend/src/stores/auth.ts` — 添加 login/register/fetchUser actions
- Modify: `frontend/src/views/LoginView.vue` — 登录表单页面
- Modify: `frontend/src/views/RegisterView.vue` — 注册表单页面
- Modify: `frontend/src/router/index.ts` — 登录后获取用户信息

- [x] **Step 1: 创建认证 API 模块**

```typescript
// frontend/src/api/auth.ts
import client from './client'

export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  password: string
  real_name: string
  department: string
  phone?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: string
  email: string
  real_name: string
  department: string
  phone: string | null
  is_active: boolean
  created_at: string
}

export async function login(form: LoginForm): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', form.email)
  params.append('password', form.password)
  const { data } = await client.post('/v1/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function register(form: RegisterForm): Promise<User> {
  const { data } = await client.post('/v1/auth/register', form)
  return data
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await client.get('/v1/auth/me')
  return data
}
```

> **设计说明:**
> - 登录接口使用 `application/x-www-form-urlencoded`，因为后端使用 `OAuth2PasswordRequestForm`
> - 注册接口使用 JSON，与后端 `UserCreate` schema 对应
> - API 层只做 HTTP 调用，不处理状态管理（状态由 Pinia store 处理）

- [x] **Step 2: 更新 auth store**

在 `frontend/src/stores/auth.ts` 中添加异步 actions：

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, register as registerApi, fetchCurrentUser } from '@/api/auth'
import type { LoginForm, RegisterForm, User } from '@/api/auth'

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

  async function login(form: LoginForm) {
    const data = await loginApi(form)
    setTokens(data.access_token, data.refresh_token)
    const userData = await fetchCurrentUser()
    user.value = userData
  }

  async function register(form: RegisterForm) {
    await registerApi(form)
  }

  async function fetchUser() {
    if (!accessToken.value) return
    const userData = await fetchCurrentUser()
    user.value = userData
  }

  return {
    accessToken, refreshToken, user,
    isAuthenticated, login, register, fetchUser, clearAuth,
  }
})
```

> **设计说明:**
> - `login()` 先获取 token，再调用 `/me` 获取用户信息，确保登录后 store 中 user 立即可用
> - `fetchUser()` 在页面刷新时调用，从 token 恢复用户状态

- [x] **Step 3: 实现登录页面**

```vue
<!-- frontend/src/views/LoginView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <div class="w-full max-w-md p-8 bg-surface-container-low rounded-md">
      <h1 class="text-2xl font-semibold text-center mb-8"
STT 音频转录</h1>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
邮箱</label>
          <input
            v-model="form.email"
            type="email"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="your@email.com"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
密码</label>
          <input
            v-model="form.password"
            type="password"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div v-if="error" class="text-sm text-red-500"
{{ error }}</div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-3 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary-dim transition-colors disabled:opacity-50"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <p class="text-center text-sm text-on-surface-variant mt-6"
        还没有账号？
        <RouterLink to="/register" class="text-primary hover:underline"
立即注册</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({ email: '', password: '' })
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''
  try {
    await authStore.login(form.value)
    router.push({ name: 'dashboard' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
```

> **设计说明:**
> - 表单提交使用 `@submit.prevent` 阻止默认行为
> - 登录成功后跳转仪表盘，失败显示后端返回的错误信息
> - 按钮 loading 状态防止重复提交

- [x] **Step 4: 实现注册页面**

```vue
<!-- frontend/src/views/RegisterView.vue -->
<template>
  <div class="min-h-screen flex items-center justify-center bg-surface">
    <div class="w-full max-w-md p-8 bg-surface-container-low rounded-md">
      <h1 class="text-2xl font-semibold text-center mb-8"
创建账号</h1>

      <form @submit.prevent="handleSubmit" class="space-y-4">
        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
邮箱</label>
          <input
            v-model="form.email"
            type="email"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="your@email.com"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
真实姓名</label>
          <input
            v-model="form.real_name"
            type="text"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="张三"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
部门</label>
          <input
            v-model="form.department"
            type="text"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="技术部"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
密码</label>
          <input
            v-model="form.password"
            type="password"
            required
            minlength="6"
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div>
          <label class="block text-sm text-on-surface-variant mb-1"
确认密码</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            required
            class="w-full px-4 py-3 bg-surface-container-high rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
            placeholder="••••••••"
          />
        </div>

        <div v-if="error" class="text-sm text-red-500"
{{ error }}</div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-3 bg-primary text-white rounded-md text-sm font-medium hover:bg-primary-dim transition-colors disabled:opacity-50"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="text-center text-sm text-on-surface-variant mt-6"
        已有账号？
        <RouterLink to="/login" class="text-primary hover:underline"
立即登录</RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = ref({
  email: '',
  password: '',
  confirmPassword: '',
  real_name: '',
  department: '',
})
const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  if (form.value.password !== form.value.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  error.value = ''
  try {
    await authStore.register({
      email: form.value.email,
      password: form.value.password,
      real_name: form.value.real_name,
      department: form.value.department,
    })
    router.push({ name: 'login' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
```

> **设计说明:**
> - 前端做密码一致性校验，避免不必要的后端请求
> - 注册成功后跳转到登录页（而非自动登录），引导用户重新输入密码确认

- [x] **Step 5: 更新路由守卫**

修改 `frontend/src/router/index.ts`，在路由守卫中添加已登录用户的用户信息获取：

```typescript
import { useAuthStore } from '@/stores/auth'

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = !!localStorage.getItem('access_token')

  if (!to.meta.public && !isAuthenticated) {
    next({ name: 'login' })
    return
  }

  if (isAuthenticated && !authStore.user) {
    try {
      await authStore.fetchUser()
    } catch {
      authStore.clearAuth()
      next({ name: 'login' })
      return
    }
  }

  next()
})
```

> **设计说明:**
> - 页面刷新时 token 仍在 localStorage，但 Pinia store 中的 user 会丢失
> - 路由守卫检测到 `access_token` 存在但 `user` 为空时，自动调用 `/me` 恢复用户状态
> - `/me` 失败（token 过期）时清除认证状态并跳转登录页

- [x] **Step 6: 提交**

```bash
git add frontend/src/api/auth.ts frontend/src/stores/auth.ts \
    frontend/src/views/LoginView.vue frontend/src/views/RegisterView.vue \
    frontend/src/router/index.ts
git commit -m "feat(task10): add auth API client and login/register pages"
```

---
