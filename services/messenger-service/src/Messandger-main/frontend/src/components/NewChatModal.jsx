import { useState } from 'react'
import { X, Search, Users, User, Megaphone } from 'lucide-react'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import Avatar from './Avatar'

export default function NewChatModal({ onClose }) {
  const [tab, setTab] = useState('private') // private | group | channel
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [selected, setSelected] = useState([])
  const [groupName, setGroupName] = useState('')
  const { searchUsers, createChat, setActiveChat } = useChatStore()
  const { user } = useAuthStore()
  const isAdmin = user && ['super_admin', 'admin'].includes(user.role)

  const handleSearch = async (q) => {
    setQuery(q)
    if (q.length > 1) {
      const r = await searchUsers(q)
      setResults(r)
    } else {
      setResults([])
    }
  }

  const handleCreatePrivate = async (userId) => {
    const chat = await createChat('private', null, [userId])
    if (chat) setActiveChat(chat)
    onClose()
  }

  const handleCreateGroup = async () => {
    if (selected.length === 0 || !groupName.trim()) return
    const chatType = tab === 'channel' ? 'channel' : 'group'
    const chat = await createChat(chatType, groupName.trim(), selected.map((u) => u.id))
    if (chat) setActiveChat(chat)
    onClose()
  }

  const toggleSelect = (user) => {
    setSelected((prev) =>
      prev.find((u) => u.id === user.id) ? prev.filter((u) => u.id !== user.id) : [...prev, user]
    )
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="text-lg font-bold text-white">Новый чат</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white"><X size={20} /></button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-3">
          <button onClick={() => setTab('private')} className={`flex-1 py-2 text-sm rounded-lg flex items-center justify-center gap-1 ${tab === 'private' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>
            <User size={14} /> Личный
          </button>
          <button onClick={() => setTab('group')} className={`flex-1 py-2 text-sm rounded-lg flex items-center justify-center gap-1 ${tab === 'group' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>
            <Users size={14} /> Группа
          </button>
          {isAdmin && (
            <button onClick={() => setTab('channel')} className={`flex-1 py-2 text-sm rounded-lg flex items-center justify-center gap-1 ${tab === 'channel' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>
              <Megaphone size={14} /> Канал
            </button>
          )}
        </div>

        {/* Search */}
        <div className="px-4 pb-2">
          {(tab === 'group' || tab === 'channel') && (
            <input type="text" value={groupName} onChange={(e) => setGroupName(e.target.value)} className="input-field mb-2" placeholder={tab === 'channel' ? 'Название канала' : 'Название группы'} />
          )}
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input type="text" value={query} onChange={(e) => handleSearch(e.target.value)} className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500" placeholder="Поиск по имени или email..." />
          </div>
        </div>

        {/* Selected for group/channel */}
        {(tab === 'group' || tab === 'channel') && selected.length > 0 && (
          <div className="px-4 pb-2 flex gap-1 flex-wrap">
            {selected.map((u) => (
              <span key={u.id} onClick={() => toggleSelect(u)} className="px-2 py-1 bg-primary-600/20 text-primary-300 rounded-full text-xs cursor-pointer hover:bg-primary-600/40">
                {u.first_name} ×
              </span>
            ))}
          </div>
        )}

        {/* Results */}
        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {results.map((u) => (
            <div key={u.id} onClick={() => tab === 'private' ? handleCreatePrivate(u.id) : toggleSelect(u)}
              title={tab !== 'private' ? 'Нажмите для добавления' : undefined}
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

        {/* Create group/channel button */}
        {(tab === 'group' || tab === 'channel') && (
          <div className="p-4 border-t border-dark-700">
            <button onClick={handleCreateGroup} disabled={!groupName.trim() || selected.length === 0} className="btn-primary w-full disabled:opacity-50">
              {tab === 'channel' ? `Создать канал (${selected.length})` : `Создать группу (${selected.length})`}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
