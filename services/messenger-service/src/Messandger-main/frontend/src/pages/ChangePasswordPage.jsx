import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Shield } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const { changePassword } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast.error('Пароли не совпадают')
      return
    }
    if (newPassword.length < 6) {
      toast.error('Пароль должен быть не менее 6 символов')
      return
    }
    const result = await changePassword(oldPassword, newPassword)
    if (result.success) {
      toast.success('Пароль изменён')
      navigate('/')
    } else {
      toast.error(result.error)
    }
  }

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-orange-600 rounded-full mb-4">
            <Shield size={32} className="text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Смена пароля</h1>
          <p className="text-dark-400 mt-2 text-sm">Ваш пароль устарел. Необходимо установить новый пароль для продолжения работы.</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-dark-900 rounded-2xl p-8 shadow-xl border border-dark-700 space-y-4">
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">Текущий пароль</label>
            <div className="relative">
              <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
              <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} className="input-field pl-10" required />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">Новый пароль</label>
            <div className="relative">
              <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="input-field pl-10" minLength={6} required />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-dark-300 mb-1">Подтвердите пароль</label>
            <div className="relative">
              <Lock size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="input-field pl-10" required />
            </div>
          </div>
          <button type="submit" className="btn-primary w-full">Сменить пароль</button>
        </form>
      </div>
    </div>
  )
}
