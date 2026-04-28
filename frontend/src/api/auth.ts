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