'use client'

import { useState, useEffect } from 'react'

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
  return process.env.NEXT_PUBLIC_VIDEO_URL || 'http://localhost:3000';
};

// Available services configuration
const getServices = (): Service[] => [
  {
    id: 'video',
    name: 'Видеохостинг',
    description: 'Корпоративная платформа для хранения и просмотра видеоматериалов ДГИ',
    icon: <Video className="w-8 h-8" />,
    url: getVideoUrl(),
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    status: 'active',
    features: ['Загрузка видео', 'Трансляции', 'Категории', 'Поиск']
  },
  {
    id: 'messenger',
    name: 'Мессенджер',
    description: 'Защищённый корпоративный мессенджер для сотрудников ДГИ',
    icon: <MessageSquare className="w-8 h-8" />,
    url: '#',
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
    url: '#',
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
    url: '#',
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
  fullName: string
  role: string
  avatar?: string
}

export default function PortalPage() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [currentTime, setCurrentTime] = useState(new Date())

  // Check auth status on mount
  useEffect(() => {
    checkAuth()
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const checkAuth = async () => {
    // In dev, try to get user from localStorage or redirect to video service auth
    const token = localStorage.getItem('token')
    if (token) {
      // TODO: Verify token with auth service
      // For now, mock user
      setUser({
        id: '1',
        username: 'employee',
        email: 'employee@dgi.mos.ru',
        fullName: 'Сотрудник ДГИ',
        role: 'user'
      })
    }
    setLoading(false)
  }

  const handleLogin = () => {
    // Redirect to video service login (which uses auth-service)
    const videoUrl = process.env.NEXT_PUBLIC_VIDEO_URL || 'http://localhost:3000'
    window.location.href = `${videoUrl}/login?redirect=${encodeURIComponent(window.location.href)}`
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  const handleServiceClick = (service: Service) => {
    if (service.status === 'active') {
      window.location.href = service.url
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-800 rounded-lg flex items-center justify-center">
                <Building2 className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900">Портал ДГИ</h1>
                <p className="text-xs text-slate-500">Единое информационное пространство</p>
              </div>
            </div>

            {/* User section */}
            <div className="flex items-center space-x-4">
              {/* Time */}
              <div className="hidden sm:block text-sm text-slate-600">
                {currentTime.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}
                <span className="mx-2 text-slate-300">|</span>
                {currentTime.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })}
              </div>

              {user ? (
                <div className="flex items-center space-x-3">
                  <div className="text-right hidden sm:block">
                    <p className="text-sm font-medium text-slate-900">{user.fullName}</p>
                    <p className="text-xs text-slate-500">{user.role}</p>
                  </div>
                  <div className="w-10 h-10 bg-gradient-to-br from-slate-100 to-slate-200 rounded-full flex items-center justify-center">
                    <User className="w-5 h-5 text-slate-600" />
                  </div>
                  <button 
                    onClick={handleLogout}
                    className="p-2 text-slate-400 hover:text-red-600 transition-colors"
                    title="Выйти"
                  >
                    <LogOut className="w-5 h-5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleLogin}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span>Войти</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Hero section */}
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-slate-900 mb-4">
            Добро пожаловать в Портал ДГИ
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Единая платформа доступа ко всем корпоративным сервисам Департамента городского имущества Москвы
          </p>
          
          {/* Stats or features */}
          <div className="flex justify-center gap-8 mt-8">
            <div className="flex items-center space-x-2 text-slate-600">
              <Shield className="w-5 h-5 text-green-500" />
              <span className="text-sm">Защищённый доступ</span>
            </div>
            <div className="flex items-center space-x-2 text-slate-600">
              <Zap className="w-5 h-5 text-yellow-500" />
              <span className="text-sm">Быстрая работа</span>
            </div>
            <div className="flex items-center space-x-2 text-slate-600">
              <Play className="w-5 h-5 text-blue-500" />
              <span className="text-sm">Видео и стримы</span>
            </div>
          </div>
        </div>

        {/* Services grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {getServices().map((service: Service, index: number) => (
            <div
              key={service.id}
              onClick={() => handleServiceClick(service)}
              className={`
                service-card relative bg-white rounded-2xl p-6 border-2 cursor-pointer
                ${service.status === 'active' 
                  ? 'border-transparent shadow-lg hover:shadow-xl cursor-pointer' 
                  : 'border-slate-200 opacity-75 cursor-not-allowed'
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
                  <h3 className="text-xl font-semibold text-slate-900 mb-2">
                    {service.name}
                  </h3>
                  <p className="text-slate-600 text-sm mb-4">
                    {service.description}
                  </p>
                  
                  {/* Features */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {service.features.map((feature: string) => (
                      <span 
                        key={feature}
                        className="px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded-md"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>

                  {/* Action button */}
                  <div className="flex items-center space-x-2">
                    <span className={`
                      text-sm font-medium
                      ${service.status === 'active' ? 'text-blue-600' : 'text-slate-400'}
                    `}>
                      {service.status === 'active' ? 'Перейти' : 'Недоступно'}
                    </span>
                    {service.status === 'active' && (
                      <ChevronRight className="w-4 h-4 text-blue-600" />
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Info section */}
        <div className="mt-16 bg-white rounded-2xl p-8 shadow-sm border border-slate-200">
          <div className="flex items-start space-x-4">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
              <Shield className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Информация безопасности
              </h3>
              <p className="text-slate-600 text-sm mb-4">
                Все данные передаются по защищённому соединению. Доступ к сервисам осуществляется 
                только после авторизации через корпоративную учётную запись.
              </p>
              <div className="flex items-center space-x-4 text-sm">
                <span className="text-slate-500">Техническая поддержка:</span>
                <a href="mailto:support@dgi.mos.ru" className="text-blue-600 hover:underline">
                  support@dgi.mos.ru
                </a>
                <span className="text-slate-300">|</span>
                <span className="text-slate-500">Телефон: +7 (495) XXX-XX-XX</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-slate-900 text-slate-400 py-8 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <Building2 className="w-6 h-6" />
              <span className="text-sm">© 2024 Департамент городского имущества Москвы</span>
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
