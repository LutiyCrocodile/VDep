'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Building2, LogIn, Eye, EyeOff, Shield } from 'lucide-react'

declare global {
  interface Window {
    ENV?: {
      NEXT_PUBLIC_VIDEO_URL?: string;
      NEXT_PUBLIC_AUTH_URL?: string;
    };
  }
}

const getAuthUrl = () => {
  if (typeof window !== 'undefined') {
    return window.ENV?.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000';
  }
  return 'http://localhost:8000';
};

export default function LoginPage() {
  const router = useRouter()
  const [loginData, setLoginData] = useState({ username: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)

    try {
      const authUrl = getAuthUrl()
      const formData = new URLSearchParams()
      formData.append('username', loginData.username)
      formData.append('password', loginData.password)

      const res = await fetch(`${authUrl}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || 'Ошибка входа')
      }

      const data = await res.json()
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)

      const meRes = await fetch(`${authUrl}/users/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      if (meRes.ok) {
        const userData = await meRes.json()
        if (userData.is_employee) {
          router.push('/')
        } else {
          setLoginError('Доступ разрешен только сотрудникам ДГИ')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Не удалось войти'
      setLoginError(message)
    } finally {
      setLoginLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-red-50/50 via-white to-[var(--dgi-bg)] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-dgi-primary to-dgi-primary-dark rounded-3xl mb-6 shadow-xl">
            <Building2 className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-dgi-text mb-2 font-heading">ДГИ Москва</h1>
          <h2 className="text-xl text-dgi-muted mb-1">Портал доступа к сервисам</h2>
          <p className="text-dgi-muted text-sm">Единая система авторизации для сотрудников</p>
        </div>

        <div className="bg-dgi-surface rounded-2xl shadow-xl border border-dgi-border p-8">
          <form onSubmit={handleLogin} className="space-y-6">
            <div>
              <label htmlFor="username" className="block text-sm font-semibold text-dgi-text mb-2">
                Логин
              </label>
              <input
                id="username"
                type="text"
                value={loginData.username}
                onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                className="w-full px-4 py-3 border border-dgi-border rounded-lg focus:ring-2 focus:ring-dgi-primary/30 focus:border-dgi-primary outline-none transition-all text-dgi-text placeholder-gray-400"
                placeholder="Введите корпоративный логин"
                required
                autoFocus
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-semibold text-dgi-text mb-2">
                Пароль
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={loginData.password}
                  onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                  className="w-full px-4 py-3 pr-12 border border-dgi-border rounded-lg focus:ring-2 focus:ring-dgi-primary/30 focus:border-dgi-primary outline-none transition-all text-dgi-text placeholder-gray-400"
                  placeholder="Введите пароль"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-dgi-muted hover:text-dgi-text transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            {loginError && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
                {loginError}
              </div>
            )}

            <button
              type="submit"
              disabled={loginLoading}
              className="dgi-btn-primary w-full font-semibold py-3 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {loginLoading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Вход в систему...
                </>
              ) : (
                <>
                  <LogIn className="w-5 h-5" />
                  Войти
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-dgi-border">
            <div className="flex items-center gap-2 text-sm text-dgi-muted">
              <Shield className="w-4 h-4 text-dgi-primary" />
              <span>Защищенная корпоративная система</span>
            </div>
          </div>
        </div>

        <div className="text-center mt-8">
          <p className="text-dgi-muted text-sm">
            Департамент городского имущества Москвы
          </p>
          <p className="text-dgi-muted text-xs mt-1">
            © 2026 Все права защищены
          </p>
        </div>
      </div>
    </div>
  )
}
