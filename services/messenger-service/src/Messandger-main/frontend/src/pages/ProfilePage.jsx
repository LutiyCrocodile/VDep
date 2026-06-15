import { useState, useEffect, useRef } from 'react'
import { ChevronLeft, Camera, Lock, User, Mail, Building2, Briefcase, AlertTriangle, LogOut, Eye, EyeOff, Users, Search, X, Check, Trash2 } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import api from '../api/axios'
import toast from 'react-hot-toast'
import Avatar from '../components/Avatar'
import { confirmDelete } from '../store/confirmStore'

const VISIBILITY_OPTIONS = [
  { key: 'all', label: 'Все', desc: 'Аватарка видна всем пользователям' },
  { key: 'contacts', label: 'Только контакты', desc: 'Только те, с кем есть переписка' },
  { key: 'selected', label: 'Выборочно', desc: 'Только выбранные пользователи' },
  { key: 'except', label: 'Все кроме', desc: 'Все, за исключением выбранных' },
]

export default function ProfilePage() {
  const { user, fetchUser, changePassword, logout } = useAuthStore()
  const navigate = useNavigate()
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [nameField, setNameField] = useState('')
  const [nameValue, setNameValue] = useState('')
  const fileRef = useRef(null)

  // Avatar visibility
  const [avatarVis, setAvatarVis] = useState('all')
  const [avatarVisList, setAvatarVisList] = useState([])
  const [showUserPicker, setShowUserPicker] = useState(false)
  const [visSearchQ, setVisSearchQ] = useState('')
  const [visSearchResults, setVisSearchResults] = useState([])

  useEffect(() => {
    if (user) {
      setAvatarVis(user.avatar_visibility || 'all')
      setAvatarVisList(user.avatar_visibility_list || [])
    }
  }, [user])

  const handleChangePassword = async () => {
    if (newPassword.length < 6) return toast.error('Пароль должен быть не менее 6 символов')
    if (newPassword !== confirmPassword) return toast.error('Пароли не совпадают')
    const result = await changePassword(oldPassword, newPassword)
    if (result.success) {
      toast.success('Пароль изменён')
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } else {
      toast.error(result.error)
    }
  }

  const handleRequestNameChange = async () => {
    if (!nameField || !nameValue.trim()) return toast.error('Заполните поля')
    try {
      await api.post('/auth/me/request-name-change', { field: nameField, new_value: nameValue.trim() })
      toast.success('Запрос отправлен в Управление информатизации')
      setNameField('')
      setNameValue('')
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post('/auth/me/avatar/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      toast.success('Аватар обновлён')
      fetchUser()
    } catch (err) {
      toast.error('Ошибка загрузки аватара')
    }
    e.target.value = ''
  }

  const handleDeleteAvatar = async () => {
    if (!user?.avatar_url) return
    if (!(await confirmDelete('Удалить аватар?'))) return
    try {
      await api.delete('/auth/me/avatar')
      toast.success('Аватар удалён')
      fetchUser()
    } catch (err) {
      toast.error('Ошибка удаления аватара')
    }
  }

  const saveAvatarVisibility = async (vis, list) => {
    try {
      await api.put('/auth/me/avatar-visibility', { visibility: vis, user_ids: list })
      toast.success('Настройки видимости сохранены')
      fetchUser()
    } catch (e) {
      toast.error('Ошибка сохранения')
    }
  }

  const handleVisChange = (vis) => {
    setAvatarVis(vis)
    if (vis === 'all' || vis === 'contacts') {
      setAvatarVisList([])
      saveAvatarVisibility(vis, [])
    }
  }

  const searchVisUsers = async (q) => {
    setVisSearchQ(q)
    if (q.length < 2) { setVisSearchResults([]); return }
    try {
      const r = await api.get(`/auth/users?q=${q}`)
      setVisSearchResults(r.data.filter(u => !avatarVisList.includes(u.id)))
    } catch (e) {}
  }

  const addVisUser = (u) => {
    const newList = [...avatarVisList, u.id]
    setAvatarVisList(newList)
    setVisSearchResults(prev => prev.filter(x => x.id !== u.id))
    setVisSearchQ('')
  }

  const removeVisUser = (id) => {
    setAvatarVisList(prev => prev.filter(x => x !== id))
  }

  const fieldLabels = { first_name: 'Имя', last_name: 'Фамилия', patronymic: 'Отчество' }

  return (
    <div className="h-screen flex bg-dark-950">
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-2xl mx-auto p-6">
          <Link to="/" className="flex items-center gap-2 text-dark-400 hover:text-white text-sm mb-6">
            <ChevronLeft size={16} /> Назад к чатам
          </Link>

          <h2 className="text-2xl font-bold text-white mb-6">Профиль</h2>

          {/* Avatar section */}
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 mb-4">
            <div className="flex items-center gap-4">
              <div className="relative">
                <Avatar name={user?.first_name} url={user?.avatar_url} size="lg" />
                <button onClick={() => fileRef.current?.click()} className="absolute -bottom-1 -right-1 w-8 h-8 bg-primary-600 hover:bg-primary-700 rounded-full flex items-center justify-center shadow-lg">
                  <Camera size={14} className="text-white" />
                </button>
                {user?.avatar_url && (
                  <button onClick={handleDeleteAvatar} className="absolute -bottom-1 -left-1 w-8 h-8 bg-red-600 hover:bg-red-700 rounded-full flex items-center justify-center shadow-lg">
                    <Trash2 size={14} className="text-white" />
                  </button>
                )}
                <input type="file" ref={fileRef} className="hidden" accept="image/*" onChange={handleAvatarUpload} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">{user?.last_name} {user?.first_name} {user?.patronymic}</h3>
                <p className="text-sm text-dark-400">{user?.position}</p>
                <p className="text-xs text-dark-500">{user?.department}</p>
              </div>
            </div>
          </div>

          {/* Avatar visibility */}
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 mb-4">
            <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Eye size={14} className="text-primary-400" /> Видимость аватарки
            </h4>
            <div className="grid grid-cols-2 gap-2 mb-3">
              {VISIBILITY_OPTIONS.map(opt => (
                <button key={opt.key} onClick={() => handleVisChange(opt.key)}
                  className={`p-3 rounded-xl text-left border transition-colors ${avatarVis === opt.key ? 'bg-primary-600/10 border-primary-500 text-white' : 'bg-dark-800 border-dark-700 text-dark-400 hover:border-dark-500'}`}>
                  <p className="text-xs font-medium">{opt.label}</p>
                  <p className="text-[10px] mt-0.5 opacity-70">{opt.desc}</p>
                </button>
              ))}
            </div>

            {(avatarVis === 'selected' || avatarVis === 'except') && (
              <div className="mt-3">
                <div className="relative mb-2">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
                  <input type="text" value={visSearchQ} onChange={(e) => searchVisUsers(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="Поиск пользователей..." />
                </div>
                {visSearchResults.length > 0 && (
                  <div className="bg-dark-800 rounded-xl max-h-32 overflow-y-auto mb-2">
                    {visSearchResults.map(u => (
                      <button key={u.id} onClick={() => addVisUser(u)} className="w-full flex items-center gap-2 px-3 py-2 hover:bg-dark-700 text-left">
                        <Avatar name={u.first_name} url={u.avatar_url} size="sm" />
                        <span className="text-sm text-white">{u.first_name} {u.last_name}</span>
                      </button>
                    ))}
                  </div>
                )}
                {avatarVisList.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {avatarVisList.map(id => (
                      <span key={id} className="flex items-center gap-1 bg-dark-800 px-2 py-1 rounded-lg text-xs text-white">
                        {id.slice(0, 8)}...
                        <button onClick={() => removeVisUser(id)} className="text-dark-400 hover:text-red-400"><X size={10} /></button>
                      </span>
                    ))}
                  </div>
                )}
                <button onClick={() => saveAvatarVisibility(avatarVis, avatarVisList)} className="btn-primary text-xs px-4 py-1.5">
                  <Check size={12} className="inline mr-1" /> Сохранить список
                </button>
              </div>
            )}
          </div>

          {/* Info section */}
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 mb-4 space-y-3">
            <h4 className="text-sm font-bold text-white mb-2">Информация</h4>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Mail size={14} className="text-dark-400" />
                <div>
                  <p className="text-[10px] text-dark-500">Email (логин)</p>
                  <p className="text-sm text-white">{user?.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <User size={14} className="text-dark-400" />
                <div>
                  <p className="text-[10px] text-dark-500">Роль</p>
                  <p className="text-sm text-white">{{super_admin: 'Суперадмин', admin: 'Администратор', head: 'Начальник', deputy_head: 'Зам. начальника', user: 'Пользователь'}[user?.role] || user?.role}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Building2 size={14} className="text-dark-400" />
                <div>
                  <p className="text-[10px] text-dark-500">Управление</p>
                  <p className="text-sm text-white">{user?.department || '—'}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Briefcase size={14} className="text-dark-400" />
                <div>
                  <p className="text-[10px] text-dark-500">Должность</p>
                  <p className="text-sm text-white">{user?.position || '—'}</p>
                </div>
              </div>
            </div>

            <div className="mt-3 p-3 bg-dark-800 rounded-xl">
              <p className="text-[10px] text-dark-500 flex items-center gap-1"><Lock size={10} /> Логин изменить нельзя. Имя и фамилию можно изменить только через запрос в Управление информатизации.</p>
            </div>
          </div>

          {/* Request name change */}
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 mb-4">
            <h4 className="text-sm font-bold text-white mb-3">Запрос на изменение ФИО</h4>
            <div className="flex gap-2 mb-2">
              {Object.entries(fieldLabels).map(([key, label]) => (
                <button key={key} onClick={() => { setNameField(key); setNameValue(user?.[key] || '') }}
                  className={`px-3 py-1.5 rounded-lg text-xs ${nameField === key ? 'bg-primary-600 text-white' : 'bg-dark-800 text-dark-400 hover:bg-dark-700'}`}>
                  {label}
                </button>
              ))}
            </div>
            {nameField && (
              <div className="flex gap-2 mt-2">
                <input type="text" value={nameValue} onChange={(e) => setNameValue(e.target.value)} className="input-field flex-1" placeholder={`Новое значение ${fieldLabels[nameField]?.toLowerCase()}`} />
                <button onClick={handleRequestNameChange} className="btn-primary text-sm">Отправить запрос</button>
              </div>
            )}
          </div>

          {/* Change password */}
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 mb-4">
            <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <Lock size={14} className="text-primary-400" /> Смена пароля
            </h4>
            {user?.password_expired && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-xl mb-3">
                <AlertTriangle size={14} className="text-red-400" />
                <p className="text-xs text-red-400">Ваш пароль истёк. Необходимо сменить пароль.</p>
              </div>
            )}
            <div className="space-y-2">
              <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} className="input-field" placeholder="Текущий пароль" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="input-field" placeholder="Новый пароль (мин. 6 символов)" />
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="input-field" placeholder="Подтвердите пароль" />
              <button onClick={handleChangePassword} disabled={!oldPassword || !newPassword} className="btn-primary text-sm disabled:opacity-50">Сменить пароль</button>
            </div>
            <p className="text-[10px] text-dark-500 mt-2">Пароль необходимо менять каждые 90 дней. При истечении аккаунт блокируется.</p>
          </div>

          {/* Logout */}
          <div className="mt-6 mb-8">
            <button onClick={() => logout()} className="w-full py-3 bg-red-600/10 hover:bg-red-600/20 border border-red-600/30 text-red-400 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-colors">
              <LogOut size={16} /> Выйти из аккаунта
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
