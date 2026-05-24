'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'

// Extend Window interface for runtime env
declare global {
  interface Window {
    ENV?: {
      NEXT_PUBLIC_VIDEO_URL?: string;
      NEXT_PUBLIC_AUTH_URL?: string;
    };
  }
}
import { 
  Video, 
  MessageSquare, 
  BarChart3, 
  Headphones, 
  User, 
  LogOut,
  LogIn,
  Building2,
  ChevronRight,
  Play,
  Shield,
  Zap
} from 'lucide-react'

// Service card interface
interface Service {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  url: string
  color: string
  bgColor: string
  status: 'active' | 'coming-soon' | 'maintenance'
  features: string[]
}

// Get service URLs from env (works with next.config.js env config)
const getVideoUrl = () => {
  if (typeof window !== 'undefined') {
    return window.ENV?.NEXT_PUBLIC_VIDEO_URL || 'http://localhost:3000';
  }
  return 'http://localhost:3000';
};

const getAuthUrl = () => {
  if (typeof window !== 'undefined') {
    return window.ENV?.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000';
  }
  return 'http://localhost:8000';
};

// Available services configuration
const getServices = (): Service[] => [
  {
    id: 'video',
    name: 'Видеохостинг',
    description: 'Корпоративная платформа для хранения и просмотра видеоматериалов ДГИ',
    icon: <Video className="w-8 h-8" />,
    url: getVideoUrl(),
    color: 'text-dgi-primary',
    bgColor: 'bg-red-50',
    status: 'active',
    features: ['Загрузка видео', 'Трансляции', 'Категории', 'Поиск']
  },
    {
      id: 'messenger',
      name: 'Мессенджер',
      description: 'Защищённый корпоративный мессенджер для сотрудников ДГИ',
      icon: <MessageSquare className="w-8 h-8" />,
      url: 'http://localhost:3001',
      color: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      status: 'coming-soon',
      features: ['Чаты', 'Группы', 'Звонки', 'Файлы']
    },
    {
      id: 'dashboard',
      name: 'Дашборд',
      description: 'Аналитическая панель с показателями и статистикой работы',
      icon: <BarChart3 className="w-8 h-8" />,
      url: 'http://localhost:3003',
      color: 'text-purple-600',
      bgColor: 'bg-purple-50',
      status: 'coming-soon',
      features: ['Отчёты', 'Графики', 'Метрики', 'Экспорт']
    },
    {
      id: 'support',
      name: 'Техподдержка',
      description: 'Система подачи заявок в техническую поддержку',
      icon: <Headphones className="w-8 h-8" />,
      url: 'http://localhost:3004',
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      status: 'coming-soon',
      features: ['Заявки', 'Чат', 'База знаний', 'Отслеживание']
    }
];

// Mock user data (replace with real auth)
interface User {
  id: string
  username: string
  email: string
  full_name?: string
  role: string
  is_employee: boolean
  avatar?: string
}

export default function PortalPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [currentTime, setCurrentTime] = useState(new Date())
  const [showLoginForm, setShowLoginForm] = useState(false)
  const [loginData, setLoginData] = useState({ username: '', password: '' })
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)
  const router = useRouter()

  useEffect(() => {
    checkAuth()

    const timer = setInterval(() => setCurrentTime(new Date()), 1000)

    // Listen for cross-service logout (e.g. from video hosting)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === 'access_token' && !e.newValue) {
        handleLogout()
      }
    }
    window.addEventListener('storage', handleStorageChange)

    return () => {
      clearInterval(timer)
      window.removeEventListener('storage', handleStorageChange)
    }
  }, [])

  const checkAuth = async () => {
    // Check if user is already authenticated
    const token = localStorage.getItem('access_token')
    
    if (!token) {
      // No token - show login form on main page
      setLoading(false)
      return
    }

    try {
      const authUrl = getAuthUrl()
      const res = await fetch(`${authUrl}/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })

      if (res.ok) {
        const userData = await res.json()
        
        // Check if user is employee
        if (!userData.is_employee) {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          // Non-employee - show login form
          setLoading(false)
          return
        }
        setUser(userData)
        setLoading(false)
      } else {
        // Token expired or invalid
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setLoading(false)
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setLoading(false)
    }
  }

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

      // Fetch user info
      const meRes = await fetch(`${authUrl}/users/me`, {
        headers: { Authorization: `Bearer ${data.access_token}` },
      })
      if (meRes.ok) {
        const userData = await meRes.json()
        if (userData.is_employee) {
          setUser(userData)
          setShowLoginForm(false)
          setLoginData({ username: '', password: '' })
        } else {
          setLoginError('Доступ разрешен только сотрудникам ДГИ')
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
    } catch (err: any) {
      setLoginError(err.message || 'Не удалось войти')
    } finally {
      setLoginLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setUser(null)
    setShowLoginForm(false)
    setLoginData({ username: '', password: '' })
  }

  const handleServiceClick = (service: Service) => {
    if (service.status === 'active') {
      const accessToken = localStorage.getItem('access_token')
      const refreshToken = localStorage.getItem('refresh_token')
      let url = service.url

      // Append tokens for cross-service auth if authenticated
      if (accessToken && refreshToken) {
        const separator = url.includes('?') ? '&' : '?'
        url += `${separator}access_token=${encodeURIComponent(accessToken)}&refresh_token=${encodeURIComponent(refreshToken)}`
      }

      window.location.href = url
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-dgi-bg flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-dgi-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[var(--dgi-bg)] via-white to-red-50/40">
      {/* Header */}
      <header className="bg-white/90 backdrop-blur-md border-b border-dgi-border sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-dgi-primary to-dgi-primary-dark rounded-lg flex items-center justify-center shadow-md">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-dgi-text font-heading">Портал ДГИ</h1>
                <p className="text-xs text-dgi-muted">Единое информационное пространство</p>
              </div>
            </div>

            {/* User section */}
            <div className="flex items-center space-x-4">
              {/* Time */}
              <div className="hidden sm:block text-sm text-dgi-muted">
                {currentTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                <span className="mx-2 text-dgi-border">|</span>
                {currentTime.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
              </div>

              {user ? (
                <div className="flex items-center space-x-3">
                  <div className="text-right hidden sm:block">
                    <p className="text-sm font-medium text-dgi-text">{user.full_name || user.username}</p>
                    <p className="text-xs text-dgi-muted uppercase tracking-wider">{user.role}</p>
                  </div>
                  <div className="w-10 h-10 bg-gradient-to-br from-dgi-primary to-dgi-primary-mid rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-white" />
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="p-2 text-dgi-muted hover:text-dgi-primary transition-colors"
                    title="Выйти"
                  >
                    <LogOut className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => router.push('/login')}
                  className="dgi-btn-primary flex items-center gap-2 px-5 py-2.5 active:scale-95"
                >
                  <LogIn className="w-5 h-5" />
                  Войти
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Auth redirect handled via /login page */}
      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-dgi-text mb-4 font-heading">
            Добро пожаловать в Портал ДГИ
          </h2>
          <p className="text-lg text-dgi-muted max-w-2xl mx-auto">
            Единая платформа доступа ко всем корпоративным сервисам Департамента городского имущества Москвы
          </p>
          
        </div>

        {/* Services grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {getServices().map((service: Service, index: number) => (
            <div
              key={service.id}
              onClick={() => handleServiceClick(service)}
              className={`
                service-card relative bg-dgi-surface rounded-2xl p-6 border-2 cursor-pointer
                ${service.status === 'active' 
                  ? 'border-transparent shadow-lg hover:shadow-xl cursor-pointer' 
                  : 'border-dgi-border opacity-75 cursor-not-allowed'
                }
              `}
              style={{
                animationDelay: `${index * 100}ms`
              }}
            >
              {/* Status badge */}
              {service.status !== 'active' && (
                <div className="absolute top-4 right-4">
                  <span className={`
                    px-2 py-1 text-xs font-medium rounded-full
                    ${service.status === 'coming-soon' 
                      ? 'bg-amber-100 text-amber-700' 
                      : 'bg-red-100 text-red-700'
                    }
                  `}>
                    {service.status === 'coming-soon' ? 'Скоро' : 'Обслуживание'}
                  </span>
                </div>
              )}

              <div className="flex items-start space-x-4">
                <div className={`
                  w-16 h-16 rounded-xl flex items-center justify-center ${service.bgColor}
                `}>
                  <div className={service.color}>
                    {service.icon}
                  </div>
                </div>
                
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-dgi-text mb-2 font-heading">
                    {service.name}
                  </h3>
                  <p className="text-dgi-muted text-sm mb-4">
                    {service.description}
                  </p>

                  {/* Action button */}
                  <div className="flex items-center space-x-2">
                    <span className={`
                      text-sm font-medium
                      ${service.status === 'active' ? 'text-dgi-primary' : 'text-dgi-muted'}
                    `}>
                      {service.status === 'active' ? 'Перейти' : 'Недоступно'}
                    </span>
                    {service.status === 'active' && (
                      <ChevronRight className="w-4 h-4 text-dgi-primary" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Info section */}
        <div className="mt-16 bg-dgi-surface rounded-2xl p-8 shadow-sm border border-dgi-border">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Shield className="w-6 h-6 text-dgi-primary" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-dgi-text mb-2 font-heading">
                Информация безопасности
              </h3>
              <p className="text-dgi-muted text-sm">
                Все данные передаются по защищённому соединению. Доступ к сервисам осуществляется 
                только после авторизации через корпоративную учётную запись.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-[#141414] text-gray-400 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <Building2 className="w-6 h-6" />
              <span className="text-sm">© 2026 Департамент городского имущества Москвы</span>
            </div>
            <div className="flex items-center space-x-6 text-sm">
              <a href="#" className="hover:text-white transition-colors">Помощь</a>
              <a href="#" className="hover:text-white transition-colors">Контакты</a>
              <span>v1.0.0</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
