import { create } from 'zustand'
import type { UserInfo } from '../types'
import { getMe, login as loginApi, register as registerApi } from '../api/auth'

interface AuthState {
  user: UserInfo | null
  token: string | null
  loading: boolean
  setAuth: (user: UserInfo, token: string) => void
  login: (username: string, password: string) => Promise<void>
  register: (username: string, password: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => {
  // 安全解析 localStorage 中的用户数据
  let storedUser = null;
  try {
    const raw = localStorage.getItem('user');
    storedUser = raw ? JSON.parse(raw) : null;
  } catch {
    storedUser = null;
  }

  return {
  user: storedUser,
  token: localStorage.getItem('token'),
  loading: false,

  setAuth: (user, token) => {
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
    set({ user, token })
  },

  login: async (username, password) => {
    const result = await loginApi({ username, password })
    const user: UserInfo = {
      id: 0,
      username: result.username,
      role: result.role as 'admin' | 'user',
      created_at: '',
    }
    useAuthStore.getState().setAuth(user, result.access_token)
  },

  register: async (username, password) => {
    await registerApi({ username, password })
  },

  logout: () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    set({ user: null, token: null })
  },

  fetchUser: async () => {
    try {
      const user = await getMe()
      set({ user })
      localStorage.setItem('user', JSON.stringify(user))
    } catch {
      useAuthStore.getState().logout()
    }
  },
}
})
