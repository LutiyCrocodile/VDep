import { create } from 'zustand'
import api from '../api/axios'
import { getPortalLoginUrl } from '../lib/portal-url'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

function readTokensFromUrl() {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')
  if (accessToken && refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_KEY, refreshToken)
    const cleanUrl = window.location.pathname + window.location.hash
    window.history.replaceState({}, document.title, cleanUrl)
  }
}

readTokensFromUrl()

export const useAuthStore = create((set, get) => ({
  token: localStorage.getItem(TOKEN_KEY) || null,
  user: null,
  loading: false,

  login: async () => {
    window.location.href = getPortalLoginUrl()
    return { success: false, error: 'Перенаправление на портал' }
  },

  fetchUser: async () => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      set({ token: null, user: null })
      return
    }
    set({ token })
    try {
      const res = await api.get('/auth/me')
      set({ user: res.data })
    } catch (error) {
      console.error('Ошибка загрузки профиля:', error)
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(REFRESH_KEY)
      set({ token: null, user: null })
    }
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    set({ token: null, user: null })
    window.location.href = getPortalLoginUrl()
  },

  changePassword: async () => ({
    success: false,
    error: 'Смена пароля выполняется через портал',
  }),
}))
