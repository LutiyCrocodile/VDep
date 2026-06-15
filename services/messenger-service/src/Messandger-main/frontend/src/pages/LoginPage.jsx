import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { MessageSquare, Mail, Lock, Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const { login, loading } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    const result = await login(email, password)
    if (result.success) {
      if (result.password_expired) {
        navigate('/change-password')
        toast('Необходимо сменить пароль', { icon: '⚠️' })
      } else {
        navigate('/')
      }
    } else {
      toast.error(result.error)
    }
  }

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl mb-4 shadow-lg shadow-primary-600/30">
            <span className="text-white font-heading font-bold text-2xl tracking-wider">ГКМ</span>
          </div>
          <h1 className="text-3xl font-heading font-bold text-white tracking-wide">Корпоративный мессенджер</h1>
          <p className="text-dark-400 mt-2">Войдите в свой рабочий аккаунт</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-dark-900 rounded-2xl p-8 shadow-xl border border-dark-700">
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">Email (логин)</label>
              <div className="relative">
                <Mail size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="i.ivanov@dgi.gov"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">Пароль</label>
              <div className="relative">
                <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10 pr-10"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-white"
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">
              {loading ? 'Вход...' : 'Войти'}
            </button>
          </div>

          <div className="mt-6 pt-4 border-t border-dark-700">
            <p className="text-center text-dark-400 text-sm">
              Нет аккаунта?{' '}
              <Link to="/access-request" className="text-primary-400 hover:text-primary-300 font-medium">
                Отправить запрос на доступ
              </Link>
            </p>
          </div>
        </form>
      </div>
    </div>
  )
}
