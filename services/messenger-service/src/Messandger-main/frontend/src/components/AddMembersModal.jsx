import { useState } from 'react'
import { X, Search, UserPlus } from 'lucide-react'
import { useChatStore } from '../store/chatStore'
import api from '../api/axios'
import toast from 'react-hot-toast'
import Avatar from './Avatar'

export default function AddMembersModal({ chatId, onClose }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState([])
  const { searchUsers, fetchChats } = useChatStore()

  const handleSearch = async (q) => {
    setQuery(q)
    if (q.length > 1) {
      const r = await searchUsers(q)
      setResults(r)
    } else {
      setResults([])
    }
  }

  const toggleSelect = (user) => {
    setSelected((prev) =>
      prev.find((u) => u.id === user.id) ? prev.filter((u) => u.id !== user.id) : [...prev, user]
    )
  }

  const handleAdd = async () => {
    if (selected.length === 0) return
    try {
      const res = await api.post(`/chats/${chatId}/members`, {
        user_ids: selected.map((u) => u.id)
      })
      toast.success(`Добавлено: ${res.data.count}`)
      fetchChats()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-md max-h-[70vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="text-lg font-bold text-white flex items-center gap-2"><UserPlus size={20} className="text-primary-400" /> Добавить участников</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white"><X size={20} /></button>
        </div>

        <div className="px-4 py-3">
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input type="text" value={query} onChange={(e) => handleSearch(e.target.value)} className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500" placeholder="Поиск по имени..." />
          </div>
        </div>

        {selected.length > 0 && (
          <div className="px-4 pb-2 flex gap-1 flex-wrap">
            {selected.map((u) => (
              <span key={u.id} onClick={() => toggleSelect(u)} className="px-2 py-1 bg-primary-600/20 text-primary-300 rounded-full text-xs cursor-pointer hover:bg-primary-600/40">
                {u.first_name} ×
              </span>
            ))}
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {results.map((u) => (
            <div key={u.id} onClick={() => toggleSelect(u)}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl cursor-pointer transition-colors ${selected.find((s) => s.id === u.id) ? 'bg-primary-600/10' : 'hover:bg-dark-800'}`}
            >
              <Avatar name={u.first_name} url={u.avatar_url} size="sm" />
              <div>
                <p className="text-sm text-white">{u.last_name} {u.first_name}</p>
                <p className="text-xs text-dark-400">{u.position || u.email}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="p-4 border-t border-dark-700">
          <button onClick={handleAdd} disabled={selected.length === 0} className="btn-primary w-full disabled:opacity-50">
            Добавить ({selected.length})
          </button>
        </div>
      </div>
    </div>
  )
}
