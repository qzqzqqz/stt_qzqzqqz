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