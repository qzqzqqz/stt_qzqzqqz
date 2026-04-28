<template>
  <div class="min-h-screen flex items-center justify-center bg-surface p-4">
    <div class="w-full max-w-sm bg-surface-container rounded-2xl p-8 shadow-sm">
      <div class="text-center mb-8">
        <h1 class="text-headline-sm font-semibold text-on-surface">创建账号</h1>
        <p class="text-body-md text-on-surface-variant mt-2">注册 STT 音频转录账号</p>
      </div>

      <form @submit.prevent="handleSubmit" class="space-y-5">
        <div>
          <label class="block text-label-md font-medium text-on-surface mb-1.5">邮箱</label>
          <input
            v-model="form.email"
            type="email"
            required
            placeholder="your@email.com"
            class="w-full px-4 py-2.5 bg-surface-container-low rounded-xl border border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div>
          <label class="block text-label-md font-medium text-on-surface mb-1.5">密码</label>
          <input
            v-model="form.password"
            type="password"
            required
            minlength="6"
            placeholder="至少 6 位字符"
            class="w-full px-4 py-2.5 bg-surface-container-low rounded-xl border border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div>
          <label class="block text-label-md font-medium text-on-surface mb-1.5">真实姓名</label>
          <input
            v-model="form.real_name"
            type="text"
            required
            placeholder="输入真实姓名"
            class="w-full px-4 py-2.5 bg-surface-container-low rounded-xl border border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div>
          <label class="block text-label-md font-medium text-on-surface mb-1.5">部门</label>
          <input
            v-model="form.department"
            type="text"
            required
            placeholder="输入所属部门"
            class="w-full px-4 py-2.5 bg-surface-container-low rounded-xl border border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div>
          <label class="block text-label-md font-medium text-on-surface mb-1.5">手机号（选填）</label>
          <input
            v-model="form.phone"
            type="tel"
            placeholder="输入手机号"
            class="w-full px-4 py-2.5 bg-surface-container-low rounded-xl border border-outline-variant text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all"
          />
        </div>

        <div v-if="error" class="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">
          {{ error }}
        </div>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2.5 bg-primary hover:bg-primary-dim disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl transition-colors"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <p class="text-center text-body-sm text-on-surface-variant mt-6">
        已有账号？
        <RouterLink to="/login" class="text-primary hover:text-primary-dim font-medium transition-colors">
          立即登录
        </RouterLink>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const form = reactive({
  email: '',
  password: '',
  real_name: '',
  department: '',
  phone: '',
})

const loading = ref(false)
const error = ref('')

async function handleSubmit() {
  loading.value = true
  error.value = ''

  try {
    const payload = {
      ...form,
      phone: form.phone || undefined,
    }
    await authStore.register(payload)
    router.push({ name: 'login' })
  } catch (err: any) {
    error.value = err.response?.data?.detail || '注册失败，请检查信息后重试'
  } finally {
    loading.value = false
  }
}
</script>