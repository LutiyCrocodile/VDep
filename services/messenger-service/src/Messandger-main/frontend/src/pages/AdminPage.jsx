import { useState, useEffect } from 'react'
import { Users, FileText, UserPlus, Shield, ChevronLeft, Bell, Send, AlertTriangle, Building2, MessageSquare, Snowflake, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../api/axios'
import toast from 'react-hot-toast'
import { confirmDelete, useConfirmStore } from '../store/confirmStore'

export default function AdminPage() {
  const [tab, setTab] = useState('requests')
  const [requests, setRequests] = useState([])
  const [users, setUsers] = useState([])
  const [profileRequests, setProfileRequests] = useState([])
  const [chats, setChats] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [departments, setDepartments] = useState([])

  // Notification form state
  const [notifType, setNotifType] = useState('announcement')
  const [notifTitle, setNotifTitle] = useState('')
  const [notifBody, setNotifBody] = useState('')
  const [notifTarget, setNotifTarget] = useState('all')
  const [notifDeptId, setNotifDeptId] = useState('')
  const [sentNotifications, setSentNotifications] = useState([])

  useEffect(() => { loadData() }, [tab])

  useEffect(() => {
    api.get('/auth/departments').then(r => setDepartments(r.data)).catch(() => {})
  }, [])

  const loadData = async () => {
    if (tab === 'requests') {
      const r = await api.get('/admin/access-requests?status=pending')
      setRequests(r.data)
    } else if (tab === 'users') {
      const r = await api.get(`/admin/users?q=${searchQuery}`)
      setUsers(r.data)
    } else if (tab === 'profile') {
      const r = await api.get('/admin/profile-requests')
      setProfileRequests(r.data)
    } else if (tab === 'chats') {
      const r = await api.get('/chats/all')
      setChats(r.data)
    } else if (tab === 'notifications') {
      try {
        const r = await api.get('/notifications/sent')
        setSentNotifications(r.data)
      } catch (e) { setSentNotifications([]) }
    }
  }

  const sendNotification = async () => {
    if (!notifTitle.trim()) return toast.error('Введите заголовок')
    try {
      const payload = {
        type: notifType,
        title: notifTitle.trim(),
        body: notifBody.trim(),
        target: notifTarget,
        department_id: notifTarget === 'department' ? notifDeptId : undefined,
      }
      const res = await api.post('/notifications/send', payload)
      toast.success(res.data.message)
      setNotifTitle('')
      setNotifBody('')
      loadData()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const approveRequest = async (id) => {
    const password = prompt('Задайте временный пароль:', 'Temp123!')
    if (!password) return
    await api.post(`/admin/access-requests/${id}/approve`, { password })
    toast.success('Пользователь создан')
    loadData()
  }

  const rejectRequest = async (id) => {
    const comment = prompt('Причина отказа:')
    await api.post(`/admin/access-requests/${id}/reject`, { comment })
    toast.success('Запрос отклонён')
    loadData()
  }

  const blockUser = async (id) => {
    const ok = await useConfirmStore.getState().ask({ title: 'Заблокировать пользователя?', message: 'Пользователь не сможет входить в систему.', confirmText: 'Заблокировать' })
    if (!ok) return
    await api.post(`/admin/users/${id}/block`)
    toast.success('Заблокирован')
    loadData()
  }

  const unblockUser = async (id) => {
    await api.post(`/admin/users/${id}/unblock`)
    toast.success('Разблокирован')
    loadData()
  }

  const freezeUser = async (id) => {
    const ok = await useConfirmStore.getState().ask({ title: 'Заморозить учётную запись?', message: 'Вход будет временно запрещён.', confirmText: 'Заморозить' })
    if (!ok) return
    await api.post(`/admin/users/${id}/freeze`)
    toast.success('Заморожен')
    loadData()
  }

  const unfreezeUser = async (id) => {
    const ok = await useConfirmStore.getState().ask({ title: 'Разморозить учётную запись?', message: 'Вход будет разрешён.', confirmText: 'Разморозить' })
    if (!ok) return
    await api.post(`/admin/users/${id}/unfreeze`)
    toast.success('Разморожен')
    loadData()
  }

  const freezeChat = async (id) => {
    const ok = await useConfirmStore.getState().ask({ title: 'Заморозить чат?', message: 'Отправка сообщений будет запрещена.', confirmText: 'Заморозить' })
    if (!ok) return
    try {
      const res = await api.post(`/chats/${id}/freeze`)
      toast.success(res.data.message)
      loadData()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const deleteChat = async (id, name) => {
    const ok = await useConfirmStore.getState().ask({ title: `Удалить чат «${name}»?`, message: 'Это действие нельзя отменить.', confirmText: 'Удалить' })
    if (!ok) return
    try {
      await api.delete(`/chats/${id}`)
      toast.success('Чат удалён')
      loadData()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const resetPassword = async (id) => {
    const ok = await useConfirmStore.getState().ask({ title: 'Сбросить пароль?', message: 'Пользователю будет установлен новый пароль.', confirmText: 'Сбросить' })
    if (!ok) return
    const password = prompt('Новый пароль:', 'Temp123!')
    if (!password) return
    await api.post(`/admin/users/${id}/reset-password`, { password })
    toast.success('Пароль сброшен')
  }

  return (
    <div className="h-screen flex bg-dark-950">
      {/* Sidebar */}
      <div className="w-64 bg-dark-900 border-r border-dark-700 flex flex-col">
        <div className="p-4 border-b border-dark-700">
          <Link to="/" className="flex items-center gap-2 text-dark-400 hover:text-white text-sm mb-3">
            <ChevronLeft size={16} /> Назад к чатам
          </Link>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Shield size={20} className="text-primary-400" /> Администрирование
          </h2>
        </div>
        <nav className="p-2 space-y-1">
          <button onClick={() => setTab('requests')} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${tab === 'requests' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-800'}`}>
            <FileText size={16} /> Запросы на доступ
          </button>
          <button onClick={() => setTab('users')} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${tab === 'users' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-800'}`}>
            <Users size={16} /> Пользователи
          </button>
          <button onClick={() => setTab('chats')} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${tab === 'chats' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-800'}`}>
            <MessageSquare size={16} /> Чаты и каналы
          </button>
          <button onClick={() => setTab('profile')} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${tab === 'profile' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-800'}`}>
            <UserPlus size={16} /> Запросы на смену ФИО
          </button>
          <button onClick={() => setTab('notifications')} className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${tab === 'notifications' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:text-white hover:bg-dark-800'}`}>
            <Bell size={16} /> Уведомления
          </button>
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {tab === 'requests' && (
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Запросы на доступ ({requests.length})</h3>
            {requests.length === 0 ? <p className="text-dark-400">Нет ожидающих запросов</p> : (
              <div className="space-y-3">
                {requests.map((r) => (
                  <div key={r.id} className="bg-dark-900 border border-dark-700 rounded-xl p-4">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="text-white font-medium">{r.last_name} {r.first_name} {r.patronymic}</p>
                        <p className="text-dark-400 text-sm">{r.email} · {r.position}</p>
                        {r.reason && <p className="text-dark-500 text-xs mt-1">Причина: {r.reason}</p>}
                      </div>
                      <div className="flex gap-2">
                        <button onClick={() => approveRequest(r.id)} className="px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg">Одобрить</button>
                        <button onClick={() => rejectRequest(r.id)} className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded-lg">Отклонить</button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'users' && (
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Управление пользователями</h3>
            <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && loadData()} className="input-field mb-4 max-w-md" placeholder="Поиск по имени или email..." />
            <div className="space-y-2">
              {users.map((u) => (
                <div key={u.id} className="bg-dark-900 border border-dark-700 rounded-xl p-3 flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">{u.last_name} {u.first_name} {u.patronymic}</p>
                    <p className="text-dark-400 text-xs">{u.email} · {u.role} {u.is_blocked ? '🔒' : ''} {u.is_frozen ? '❄️' : ''}</p>
                  </div>
                  <div className="flex gap-1">
                    {!u.is_blocked && <button onClick={() => blockUser(u.id)} className="px-2 py-1 bg-red-600/20 text-red-400 text-xs rounded hover:bg-red-600/40">Блок</button>}
                    {u.is_blocked && <button onClick={() => unblockUser(u.id)} className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded hover:bg-green-600/40">Разблок</button>}
                    {!u.is_frozen && <button onClick={() => freezeUser(u.id)} className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded hover:bg-blue-600/40">Заморозить</button>}
                    {u.is_frozen && <button onClick={() => unfreezeUser(u.id)} className="px-2 py-1 bg-green-600/20 text-green-400 text-xs rounded hover:bg-green-600/40">Разморозить</button>}
                    <button onClick={() => resetPassword(u.id)} className="px-2 py-1 bg-orange-600/20 text-orange-400 text-xs rounded hover:bg-orange-600/40">Сброс пароля</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'chats' && (
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Управление чатами и каналами ({chats.length})</h3>
            <div className="space-y-2">
              {chats.map((chat) => (
                <div key={chat.id} className="bg-dark-900 border border-dark-700 rounded-xl p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="text-white text-sm font-medium flex items-center gap-2">
                        {chat.chat_type === 'group' && <MessageSquare size={14} className="text-blue-400" />}
                        {chat.chat_type === 'channel' && <MessageSquare size={14} className="text-green-400" />}
                        {chat.is_news_channel && <MessageSquare size={14} className="text-yellow-400" />}
                        {chat.name || 'Без названия'}
                      </p>
                      <p className="text-dark-400 text-xs">
                        {chat.chat_type === 'group' ? 'Группа' : chat.chat_type === 'channel' ? 'Канал' : 'Чат'} · {chat.members_count} участников
                        {chat.is_frozen && ' · ❄️ Заморожен'}
                      </p>
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => freezeChat(chat.id)} className={`px-2 py-1 text-xs rounded ${chat.is_frozen ? 'bg-green-600/20 text-green-400 hover:bg-green-600/40' : 'bg-blue-600/20 text-blue-400 hover:bg-blue-600/40'}`}>
                        <Snowflake size={12} />
                      </button>
                      {chat.chat_type !== 'private' && !(chat.is_news_channel && chat.name === 'Новости ДГИ') && (
                        <button onClick={() => deleteChat(chat.id, chat.name)} className="px-2 py-1 bg-red-600/20 text-red-400 text-xs rounded hover:bg-red-600/40">
                          <Trash2 size={12} />
                        </button>
                      )}
                    </div>
                  </div>
                  {chat.description && <p className="text-dark-500 text-xs mb-2">{chat.description}</p>}
                  <div className="flex flex-wrap gap-1">
                    {chat.members?.slice(0, 5).map((m) => (
                      <span key={m.user_id} className="text-[10px] bg-dark-800 text-dark-300 px-2 py-0.5 rounded">
                        {m.first_name} {m.last_name} ({m.role})
                      </span>
                    ))}
                    {chat.members?.length > 5 && <span className="text-[10px] text-dark-500">+{chat.members.length - 5} ещё</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'profile' && (
          <div>
            <h3 className="text-xl font-bold text-white mb-4">Запросы на смену ФИО ({profileRequests.length})</h3>
            {profileRequests.length === 0 ? <p className="text-dark-400">Нет ожидающих запросов</p> : (
              <div className="space-y-3">
                {profileRequests.map((r) => (
                  <div key={r.id} className="bg-dark-900 border border-dark-700 rounded-xl p-4 flex justify-between items-center">
                    <div>
                      <p className="text-white text-sm">Поле: <span className="text-primary-400">{r.field_name}</span></p>
                      <p className="text-dark-400 text-xs">«{r.old_value}» → «{r.new_value}»</p>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={async () => { await api.post(`/admin/profile-requests/${r.id}/approve`); toast.success('Одобрено'); loadData() }} className="px-3 py-1 bg-green-600 text-white text-xs rounded-lg">Одобрить</button>
                      <button onClick={async () => { await api.post(`/admin/profile-requests/${r.id}/reject`); toast.success('Отклонено'); loadData() }} className="px-3 py-1 bg-red-600 text-white text-xs rounded-lg">Отклонить</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {tab === 'notifications' && (
          <div className="max-w-2xl">
            <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2"><Bell size={22} className="text-primary-400" /> Отправить уведомление</h3>

            <div className="bg-dark-900 border border-dark-700 rounded-xl p-5 space-y-4 mb-6">
              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5">Тип уведомления</label>
                <div className="flex gap-2">
                  {[
                    { value: 'announcement', label: 'Объявление', icon: <Send size={14} /> },
                    { value: 'warning', label: 'Предупреждение', icon: <AlertTriangle size={14} /> },
                    { value: 'info', label: 'Информация', icon: <Bell size={14} /> },
                  ].map((t) => (
                    <button key={t.value} onClick={() => setNotifType(t.value)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs ${notifType === t.value ? 'bg-primary-600 text-white' : 'bg-dark-800 text-dark-400 hover:bg-dark-700'}`}>
                      {t.icon} {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5">Получатели</label>
                <div className="flex gap-2 flex-wrap">
                  {[
                    { value: 'all', label: 'Все пользователи' },
                    { value: 'department', label: 'Управление' },
                  ].map((t) => (
                    <button key={t.value} onClick={() => setNotifTarget(t.value)}
                      className={`px-3 py-1.5 rounded-lg text-xs ${notifTarget === t.value ? 'bg-primary-600 text-white' : 'bg-dark-800 text-dark-400 hover:bg-dark-700'}`}>
                      {t.label}
                    </button>
                  ))}
                </div>
                {notifTarget === 'department' && (
                  <select value={notifDeptId} onChange={(e) => setNotifDeptId(e.target.value)} className="input-field mt-2">
                    <option value="">Выберите управление...</option>
                    {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5">Заголовок</label>
                <input type="text" value={notifTitle} onChange={(e) => setNotifTitle(e.target.value)} className="input-field" placeholder="Тема уведомления..." />
              </div>

              <div>
                <label className="block text-xs font-medium text-dark-300 mb-1.5">Текст сообщения</label>
                <textarea value={notifBody} onChange={(e) => setNotifBody(e.target.value)} className="input-field" rows={4} placeholder="Подробный текст уведомления...&#10;&#10;Пример (email на английском):&#10;Dear colleagues, please be informed that the system maintenance is scheduled for this Saturday from 10:00 PM to 6:00 AM. All services will be temporarily unavailable." />
              </div>

              <button onClick={sendNotification} disabled={!notifTitle.trim()} className="btn-primary flex items-center gap-2 disabled:opacity-50">
                <Send size={16} /> Отправить уведомление
              </button>
            </div>

            <h4 className="text-lg font-bold text-white mb-3">История отправленных</h4>
            <div className="space-y-2">
              {sentNotifications.length === 0 ? <p className="text-dark-400 text-sm">Пока нет отправленных</p> : (
                sentNotifications.map((n) => (
                  <div key={n.id} className="bg-dark-900 border border-dark-700 rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1">
                      {n.type === 'warning' ? <AlertTriangle size={14} className="text-orange-400" /> : <Bell size={14} className="text-primary-400" />}
                      <span className="text-sm font-medium text-white">{n.title}</span>
                      <span className="text-[10px] text-dark-500 ml-auto">{new Date(new Date(n.created_at).getTime() + 3 * 60 * 60 * 1000).toLocaleString('ru')}</span>
                    </div>
                    {n.body && <p className="text-xs text-dark-400 ml-6">{n.body}</p>}
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
