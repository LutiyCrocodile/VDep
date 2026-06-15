import { useEffect, useState } from 'react'
import { Clock, X, Trash2, CalendarClock } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'
import { confirmDelete } from '../store/confirmStore'

export default function ScheduledMessagesModal({ chatId, onClose }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const res = await api.get(`/chats/${chatId}/messages/scheduled`)
      setItems(res.data || [])
    } catch (e) {
      toast.error('Не удалось загрузить запланированные сообщения')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [chatId])

  const handleCancel = async (id) => {
    if (!(await confirmDelete('Отменить отправку этого запланированного сообщения?'))) return
    try {
      await api.delete(`/chats/${chatId}/messages/scheduled/${id}`)
      setItems((prev) => prev.filter((m) => m.id !== id))
      toast.success('Запланированное сообщение отменено')
    } catch (e) {
      toast.error('Ошибка')
    }
  }

  const fmt = (iso) => {
    if (!iso) return ''
    const d = new Date(iso)
    const adjustedD = new Date(d.getTime() + 3 * 60 * 60 * 1000)
    return adjustedD.toLocaleString('ru', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <CalendarClock size={20} className="text-primary-400" />
            Запланированные сообщения
          </h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white"><X size={20} /></button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loading ? (
            <p className="text-center text-dark-400 text-sm py-6">Загрузка...</p>
          ) : items.length === 0 ? (
            <div className="text-center py-10">
              <Clock size={36} className="mx-auto text-dark-600 mb-2" />
              <p className="text-dark-400 text-sm">Нет запланированных сообщений</p>
              <p className="text-dark-500 text-xs mt-1">Используйте кнопку «Часы» в поле ввода, чтобы запланировать отправку</p>
            </div>
          ) : (
            items.map((m) => (
              <div key={m.id} className="bg-dark-800 border border-dark-700 rounded-xl p-3 flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-primary-500/15 flex items-center justify-center flex-shrink-0">
                  <Clock size={16} className="text-primary-400" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-white whitespace-pre-wrap break-words">{m.content}</p>
                  <p className="text-[11px] text-primary-300 mt-1.5 font-medium flex items-center gap-1">
                    <CalendarClock size={11} /> Отправка: {fmt(m.scheduled_at)}
                  </p>
                </div>
                <button onClick={() => handleCancel(m.id)} className="p-1.5 text-dark-400 hover:text-red-400 hover:bg-dark-700 rounded-lg transition-colors" title="Отменить">
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="p-3 border-t border-dark-700 text-[11px] text-dark-500 text-center">
          Сообщения отправляются автоматически в указанное время
        </div>
      </div>
    </div>
  )
}
