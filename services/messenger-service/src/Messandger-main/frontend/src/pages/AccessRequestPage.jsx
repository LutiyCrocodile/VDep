import { useState, useEffect } from 'react'
import { getPortalLoginUrl } from '../lib/portal-url'
import { MessageSquare, User, Mail, Phone, Building, Briefcase, FileText } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'

export default function AccessRequestPage() {
  const [form, setForm] = useState({
    first_name: '', last_name: '', patronymic: '',
    email: '', phone: '', department_id: '', division_id: '',
    position: '', reason: '',
  })
  const [departments, setDepartments] = useState([])
  const [divisions, setDivisions] = useState([])
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    api.get('/auth/departments').then((r) => setDepartments(r.data)).catch(() => {})
  }, [])

  useEffect(() => {
    if (form.department_id) {
      api.get(`/auth/divisions/${form.department_id}`).then((r) => setDivisions(r.data)).catch(() => {})
    } else {
      setDivisions([])
    }
  }, [form.department_id])

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/auth/access-request', form)
      setSubmitted(true)
      toast.success('Запрос отправлен!')
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Ошибка отправки')
    }
    setLoading(false)
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-600 rounded-full mb-4">
            <FileText size={32} className="text-white" />
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Запрос отправлен</h2>
          <p className="text-dark-400 mb-6">
            Ваш запрос передан в Управление информатизации. После одобрения вам будут высланы данные для входа.
          </p>
          <a href={getPortalLoginUrl()} className="btn-primary inline-block">Вернуться на портал</a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-950 flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl mb-3 shadow-lg shadow-primary-600/30">
            <span className="text-white font-heading font-bold text-xl tracking-wider">ГКМ</span>
          </div>
          <h1 className="text-2xl font-heading font-bold text-white tracking-wide">Запрос на доступ</h1>
          <p className="text-dark-400 mt-1 text-sm">Заполните форму для получения доступа к мессенджеру</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-dark-900 rounded-2xl p-6 shadow-xl border border-dark-700">
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Фамилия *</label>
                <input type="text" name="last_name" value={form.last_name} onChange={handleChange} className="input-field" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Имя *</label>
                <input type="text" name="first_name" value={form.first_name} onChange={handleChange} className="input-field" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Отчество</label>
                <input type="text" name="patronymic" value={form.patronymic} onChange={handleChange} className="input-field" />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Email *</label>
                <input type="email" name="email" value={form.email} onChange={handleChange} className="input-field" placeholder="i.ivanov@dgi.gov" required />
              </div>
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Телефон</label>
                <input type="tel" name="phone" value={form.phone} onChange={handleChange} className="input-field" placeholder="+7..." />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-dark-300 mb-1">Управление *</label>
              <select name="department_id" value={form.department_id} onChange={handleChange} className="input-field" required>
                <option value="">Выберите управление</option>
                {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>

            {divisions.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1">Отдел</label>
                <select name="division_id" value={form.division_id} onChange={handleChange} className="input-field">
                  <option value="">Выберите отдел</option>
                  {divisions.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                </select>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-dark-300 mb-1">Должность</label>
              <input type="text" name="position" value={form.position} onChange={handleChange} className="input-field" placeholder="Ведущий специалист" />
            </div>

            <div>
              <label className="block text-xs font-medium text-dark-300 mb-1">Причина запроса</label>
              <textarea name="reason" value={form.reason} onChange={handleChange} className="input-field" rows={2} placeholder="Необходим доступ для рабочей переписки..." />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full disabled:opacity-50">
              {loading ? 'Отправка...' : 'Отправить запрос'}
            </button>
          </div>

          <p className="text-center text-dark-400 mt-4 text-sm">
            Уже есть аккаунт?{' '}
            <a href={getPortalLoginUrl()} className="text-primary-400 hover:text-primary-300 font-medium">Войти через портал</a>
          </p>
        </form>
      </div>
    </div>
  )
}
