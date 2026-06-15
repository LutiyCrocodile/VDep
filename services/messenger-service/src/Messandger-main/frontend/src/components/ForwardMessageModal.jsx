import { useState } from 'react'
import { X, Forward, Search } from 'lucide-react'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import Avatar from './Avatar'
import api from '../api/axios'
import toast from 'react-hot-toast'

export default function ForwardMessageModal({ message, onClose }) {
  const { chats } = useChatStore()
  const { user } = useAuthStore()
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [sending, setSending] = useState(false)

  const items = chats
    .filter((c) => c.chat_type !== 'saved' || true) // include Saved
    .map((c) => ({ chat: c, name: getName(c, user) }))
    .filter((it) => it.name.toLowerCase().includes(query.toLowerCase()))

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const submit = async () => {
    if (selected.size === 0) return
    setSending(true)
    try {
      await api.post(`/chats/${message.chat_id}/messages/${message.id}/forward`, {
        target_chat_ids: Array.from(selected),
      })
      toast.success(`Переслано в ${selected.size} чат(ов)`)
      onClose()
    } catch (e) {
      toast.error('Ошибка пересылки')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-dark-900 rounded-2xl border border-dark-700 w-full max-w-md max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Forward size={18} className="text-primary-400" />
            <h3 className="font-heading font-bold text-white">Переслать в чат</h3>
          </div>
          <button onClick={onClose} className="p-1 text-dark-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="p-3 border-b border-dark-700">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500"
              placeholder="Поиск чата..."
            />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {items.length === 0 ? (
            <p className="text-center text-dark-400 text-sm py-8">Ничего не найдено</p>
          ) : (
            items.map(({ chat, name }) => (
              <button
                key={chat.id}
                onClick={() => toggle(chat.id)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-left transition-colors ${selected.has(chat.id) ? 'bg-primary-600/20 ring-1 ring-primary-500' : 'hover:bg-dark-800'}`}
              >
                <Avatar name={name} url={chat.avatar_url} size="sm" />
                <span className="flex-1 text-sm text-white truncate">{name}</span>
                {selected.has(chat.id) && <span className="text-xs text-primary-400 font-medium">✓</span>}
              </button>
            ))
          )}
        </div>
        <div className="p-3 border-t border-dark-700 flex items-center justify-between">
          <p className="text-xs text-dark-400">Выбрано: {selected.size}</p>
          <button
            onClick={submit}
            disabled={selected.size === 0 || sending}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-xl disabled:opacity-40"
          >
            {sending ? 'Отправка...' : 'Переслать'}
          </button>
        </div>
      </div>
    </div>
  )
}

function getName(chat, user) {
  if (chat.chat_type === 'saved') return 'Избранное'
  if (chat.is_news_channel) return chat.name || 'Новости'
  if (chat.chat_type === 'private') {
    const other = chat.members?.find((m) => m.user_id !== user?.id)
    return other ? `${other.first_name} ${other.last_name}` : 'Чат'
  }
  return chat.name || 'Групповой чат'
}
