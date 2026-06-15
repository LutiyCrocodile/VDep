import { create } from 'zustand'
import { getPortalLoginUrl } from './portal-url'

const TOKEN_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

function readTokensFromUrl() {
  if (typeof window === 'undefined') return
  const params = new URLSearchParams(window.location.search)
  const accessToken = params.get('access_token')
  const refreshToken = params.get('refresh_token')
  console.log('readTokensFromUrl:', { accessToken: !!accessToken, refreshToken: !!refreshToken })
  if (accessToken && refreshToken) {
    localStorage.setItem(TOKEN_KEY, accessToken)
    localStorage.setItem(REFRESH_KEY, refreshToken)
    const cleanUrl = window.location.pathname + window.location.hash
    window.history.replaceState({}, document.title, cleanUrl)
    console.log('Tokens saved to localStorage')
  }
}

readTokensFromUrl()

// API client with automatic token injection
export const apiFetch = async (url, options = {}) => {
  const token = localStorage.getItem(TOKEN_KEY)
  const headers = { ...options.headers }
  
  // Не устанавливаем Content-Type для FormData
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return fetch(url, { ...options, headers })
}

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
    console.log('fetchUser called, token:', !!token)
    if (!token) {
      set({ token: null, user: null })
      return
    }
    set({ token })
    try {
      const authUrl = import.meta.env.VITE_AUTH_URL || 'http://localhost:8000'
      console.log('Fetching user from:', authUrl)
      const res = await fetch(`${authUrl}/users/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      console.log('User fetch response:', res.status)
      if (res.ok) {
        const userData = await res.json()
        const dashboardRole = userData.services?.dashboard?.role || ''
        console.log('User data:', { username: userData.username, dashboardRole })
        set({
          user: {
            ...userData,
            dashboard_role: dashboardRole
          }
        })
      } else {
        throw new Error('Failed to fetch user')
      }
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
    localStorage.removeItem('user_role')
    localStorage.removeItem('username')
    set({ token: null, user: null })
    window.location.href = getPortalLoginUrl()
  },
}))
