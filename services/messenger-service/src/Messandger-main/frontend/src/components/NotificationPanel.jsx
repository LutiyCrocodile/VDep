import { useState, useEffect, useRef } from 'react'
import { Bell, X, CheckCheck, AlertTriangle, Info, Megaphone, Trash2, Filter } from 'lucide-react'
import api from '../api/axios'
import { confirmDelete } from '../store/confirmStore'

export default function NotificationPanel() {
  const [open, setOpen] = useState(false)
  const [notifications, setNotifications] = useState([])
  const [unread, setUnread] = useState(0)
  const [filter, setFilter] = useState('all') // all, unread, warning, announcement, info
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const panelRef = useRef(null)
  const buttonRef = useRef(null)

  // Высчитываем координаты так, чтобы панель не уходила за края экрана
  const recalcPosition = () => {
    const btn = buttonRef.current
    if (!btn) return
    const rect = btn.getBoundingClientRect()
    const panelW = 384  // w-96
    const margin = 8
    // По умолчанию открываем справа от кнопки (sidebar слева → панель в основной области)
    let left = rect.right + margin
    if (left + panelW > window.innerWidth - margin) {
      // Не помещается справа — открываем слева
      left = Math.max(margin, rect.left - panelW - margin)
    }
    const top = Math.min(rect.bottom + margin, window.innerHeight - 100)
    setPos({ top, left })
  }

  const fetchNotifications = async () => {
    try {
      const [nRes, cRes] = await Promise.all([
        api.get('/notifications/?limit=50'),
        api.get('/notifications/unread-count')
      ])
      setNotifications(nRes.data)
      setUnread(cRes.data.count)
    } catch (e) {}
  }

  useEffect(() => {
    fetchNotifications()
    const interval = setInterval(fetchNotifications, 15000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (
        panelRef.current && !panelRef.current.contains(e.target) &&
        buttonRef.current && !buttonRef.current.contains(e.target)
      ) setOpen(false)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  useEffect(() => {
    if (!open) return
    recalcPosition()
    window.addEventListener('resize', recalcPosition)
    window.addEventListener('scroll', recalcPosition, true)
    return () => {
      window.removeEventListener('resize', recalcPosition)
      window.removeEventListener('scroll', recalcPosition, true)
    }
  }, [open])

  const markRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`)
      setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n))
      setUnread((c) => Math.max(0, c - 1))
    } catch (e) {}
  }

  const markAllRead = async () => {
    try {
      await api.post('/notifications/read-all')
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
      setUnread(0)
    } catch (e) {}
  }

  const deleteNotification = async (id, e) => {
    e.stopPropagation()
    if (!(await confirmDelete('Удалить это уведомление?'))) return
    try {
      await api.delete(`/notifications/${id}`)
      setNotifications((prev) => prev.filter((n) => n.id !== id))
    } catch (e) {}
  }

  const getIcon = (type) => {
    switch (type) {
      case 'warning': return <div className="w-7 h-7 rounded-full bg-orange-500/15 flex items-center justify-center flex-shrink-0"><AlertTriangle size={13} className="text-orange-400" /></div>
      case 'announcement': return <div className="w-7 h-7 rounded-full bg-primary-500/15 flex items-center justify-center flex-shrink-0"><Megaphone size={13} className="text-primary-400" /></div>
      case 'info': return <div className="w-7 h-7 rounded-full bg-blue-500/15 flex items-center justify-center flex-shrink-0"><Info size={13} className="text-blue-400" /></div>
      default: return <div className="w-7 h-7 rounded-full bg-dark-700 flex items-center justify-center flex-shrink-0"><Bell size={13} className="text-dark-400" /></div>
    }
  }

  const getTypeLabel = (type) => {
    switch (type) {
      case 'warning': return { text: 'Предупреждение', cls: 'bg-orange-500/15 text-orange-400' }
      case 'announcement': return { text: 'Объявление', cls: 'bg-primary-500/15 text-primary-400' }
      case 'info': return { text: 'Информация', cls: 'bg-blue-500/15 text-blue-400' }
      default: return { text: 'Уведомление', cls: 'bg-dark-700 text-dark-400' }
    }
  }

  const formatTime = (dateStr) => {
    if (!dateStr) return ''
    const d = new Date(dateStr)
    const adjustedD = new Date(d.getTime() + 3 * 60 * 60 * 1000)
    const now = new Date()
    const diff = now - adjustedD
    if (diff < 60000) return 'только что'
    if (diff < 3600000) return `${Math.floor(diff / 60000)} мин назад`
    if (diff < 86400000) return `сегодня в ${adjustedD.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}`
    const yesterday = new Date(now); yesterday.setDate(yesterday.getDate() - 1)
    if (adjustedD.toDateString() === yesterday.toDateString()) return `вчера в ${adjustedD.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}`
    return adjustedD.toLocaleDateString('ru', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
  }

  const filtered = notifications.filter(n => {
    if (filter === 'unread') return !n.is_read
    if (filter === 'warning' || filter === 'announcement' || filter === 'info') return n.type === filter
    return true
  })

  const filters = [
    { key: 'all', label: 'Все' },
    { key: 'unread', label: `Непрочит.${unread > 0 ? ` (${unread})` : ''}` },
    { key: 'warning', label: 'Предупр.' },
    { key: 'announcement', label: 'Объявл.' },
  ]

  return (
    <div className="relative" ref={panelRef}>
      <button onClick={() => { setOpen(!open); if (!open) fetchNotifications() }} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors relative" title="Уведомления">
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center animate-pulse">
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div 
          className="absolute w-96 bg-dark-900 border border-dark-700 rounded-2xl shadow-2xl z-50 max-h-[75vh] flex flex-col"
          style={{ top: pos.top, left: pos.left }}
        >
          {/* Header */}
          <div className="px-4 py-3 border-b border-dark-700">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <Bell size={15} className="text-primary-400" /> Уведомления
                {unread > 0 && <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/20 text-red-400">{unread}</span>}
              </h4>
              <div className="flex gap-1">
                {unread > 0 && (
                  <button onClick={markAllRead} className="p-1.5 rounded-lg hover:bg-dark-700 text-primary-400 hover:text-primary-300 transition-colors" title="Прочитать все">
                    <CheckCheck size={15} />
                  </button>
                )}
                <button onClick={() => setOpen(false)} className="p-1.5 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors"><X size={15} /></button>
              </div>
            </div>
            {/* Filter tabs */}
            <div className="flex gap-1">
              {filters.map(f => (
                <button key={f.key} onClick={() => setFilter(f.key)}
                  className={`px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors ${filter === f.key ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800 hover:text-dark-300'}`}>
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notification list */}
          <div className="flex-1 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-8 text-center text-dark-400">
                <Bell size={36} className="mx-auto mb-3 opacity-20" />
                <p className="text-sm font-medium">Нет уведомлений</p>
                <p className="text-[11px] mt-1 opacity-60">{filter !== 'all' ? 'Попробуйте другой фильтр' : 'Уведомления появятся здесь'}</p>
              </div>
            ) : (
              filtered.map((n) => {
                const typeLabel = getTypeLabel(n.type)
                return (
                  <div
                    key={n.id}
                    onClick={() => !n.is_read && markRead(n.id)}
                    className={`group px-4 py-3 border-b border-dark-800/50 cursor-pointer hover:bg-dark-800/40 transition-all ${!n.is_read ? 'bg-primary-500/5 border-l-2 border-l-primary-500' : 'border-l-2 border-l-transparent'}`}
                  >
                    <div className="flex items-start gap-3">
                      {getIcon(n.type)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className={`text-xs font-semibold truncate ${!n.is_read ? 'text-white' : 'text-dark-300'}`}>{n.title}</p>
                          {!n.is_read && <span className="w-2 h-2 rounded-full bg-primary-500 flex-shrink-0 animate-pulse" />}
                        </div>
                        {n.body && <p className={`text-[11px] mt-0.5 line-clamp-2 leading-relaxed ${!n.is_read ? 'text-dark-300' : 'text-dark-500'}`}>{n.body}</p>}
                        <div className="flex items-center gap-2 mt-1.5">
                          <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${typeLabel.cls}`}>{typeLabel.text}</span>
                          <span className="text-[10px] text-dark-500">{formatTime(n.created_at)}</span>
                        </div>
                      </div>
                      <button onClick={(e) => deleteNotification(n.id, e)} className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-dark-700 text-dark-500 hover:text-red-400 transition-all flex-shrink-0" title="Удалить">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}
    </div>
  )
}
