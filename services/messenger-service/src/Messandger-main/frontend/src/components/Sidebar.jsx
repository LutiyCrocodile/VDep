import { useState, useEffect, useRef } from 'react'
import { Search, Plus, LogOut, Shield, MessageCircle, Phone, Star, Newspaper, UserCircle, Sun, Moon, GripHorizontal } from 'lucide-react'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import { usePresenceStore } from '../store/presenceStore'
import { useThemeStore } from '../store/themeStore'
import { Link } from 'react-router-dom'
import NewChatModal from './NewChatModal'
import NotificationPanel from './NotificationPanel'
import Avatar from './Avatar'

export default function Sidebar({ activeTab, onTabChange }) {
  const [search, setSearch] = useState('')
  const [showNewChat, setShowNewChat] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(() => {
    const saved = localStorage.getItem('sidebar_width')
    return saved ? parseInt(saved, 10) : 320
  })
  const [isResizing, setIsResizing] = useState(false)
  const sidebarRef = useRef(null)
  const { user, logout } = useAuthStore()
  const { chats, activeChat, setActiveChat } = useChatStore()

  useEffect(() => {
    localStorage.setItem('sidebar_width', sidebarWidth)
  }, [sidebarWidth])

  const handleMouseDown = (e) => {
    setIsResizing(true)
    e.preventDefault()
  }

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isResizing && sidebarRef.current) {
        const newWidth = e.clientX - sidebarRef.current.getBoundingClientRect().left
        if (newWidth >= 250 && newWidth <= 600) {
          setSidebarWidth(newWidth)
        }
      }
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  const filteredChats = chats.filter((chat) => {
    const chatName = getChatName(chat, user)
    return chatName.toLowerCase().includes(search.toLowerCase())
  })

  const isAdmin = user && ['super_admin', 'admin'].includes(user.role)
  const { theme, toggleTheme } = useThemeStore()

  return (
    <div 
      ref={sidebarRef}
      className="bg-dark-900 border-r border-dark-700 flex flex-col h-full relative"
      style={{ width: `${sidebarWidth}px`, minWidth: '250px', maxWidth: '600px' }}
    >
      {/* Header */}
      <div className="p-4 border-b border-dark-700">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <Avatar name={user?.first_name} url={user?.avatar_url} size="sm" />
            <div>
              <p className="font-medium text-white text-sm">{user?.first_name} {user?.last_name}</p>
              <p className="text-xs text-dark-400">{user?.position || user?.role}</p>
            </div>
          </div>
          <div className="flex gap-1">
            <NotificationPanel />
            <button onClick={toggleTheme} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <Link to="/profile" className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Профиль">
              <UserCircle size={18} />
            </Link>
            {isAdmin && (
              <Link to="/admin" className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-primary-400 transition-colors" title="Админ-панель">
                <Shield size={18} />
              </Link>
            )}
            <button onClick={() => setShowNewChat(true)} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Новый чат">
              <Plus size={18} />
            </button>
            <button onClick={logout} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-red-400 transition-colors" title="Выйти">
              <LogOut size={18} />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-3">
          <button onClick={() => onTabChange('chats')} className={`flex-1 py-1.5 text-xs font-medium rounded-lg flex items-center justify-center gap-1 ${activeTab === 'chats' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>
            <MessageCircle size={14} /> Чаты
          </button>
          <button onClick={() => onTabChange('calls')} className={`flex-1 py-1.5 text-xs font-medium rounded-lg flex items-center justify-center gap-1 ${activeTab === 'calls' ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>
            <Phone size={14} /> Звонки
          </button>
        </div>

        {activeTab === 'chats' && (
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)} className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500" placeholder="Поиск чатов..." />
          </div>
        )}
      </div>

      {/* Chat List */}
      {activeTab === 'chats' && (
        <div className="flex-1 overflow-y-auto flex flex-col">
          <div className="flex-1">
            {filteredChats.length === 0 ? (
              <div className="p-6 text-center text-dark-400">
                <MessageCircle size={32} className="mx-auto mb-2 opacity-50" />
                <p className="text-sm">Нет чатов</p>
              </div>
            ) : (
              filteredChats.map((chat) => (
                <ChatItem key={chat.id} chat={chat} user={user} isActive={activeChat?.id === chat.id} onClick={() => setActiveChat(chat)} />
              ))
            )}
          </div>
          {/* New chat button at bottom */}
          <div className="p-3 border-t border-dark-700">
            <button onClick={() => setShowNewChat(true)} className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 transition-colors">
              <Plus size={16} /> Новый чат
            </button>
          </div>
        </div>
      )}

      {showNewChat && <NewChatModal onClose={() => setShowNewChat(false)} />}
      
      {/* Resize handle */}
      <div
        className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-primary-500 transition-colors z-10"
        onMouseDown={handleMouseDown}
        style={{ cursor: isResizing ? 'col-resize' : 'default' }}
      >
        <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-dark-600 hover:bg-primary-500 rounded-l transition-colors">
          <GripHorizontal size={12} className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-dark-400" />
        </div>
      </div>
    </div>
  )
}

function ChatItem({ chat, user, isActive, onClick }) {
  const chatName = getChatName(chat, user)
  const presence = usePresenceStore((s) => s.presence)
  const icon = chat.chat_type === 'saved' ? <Star size={14} className="text-yellow-400" /> :
               chat.is_news_channel ? <Newspaper size={14} className="text-green-400" /> : null

  const otherMember = chat.chat_type === 'private' ? chat.members?.find((m) => m.user_id !== user?.id) : null
  const avatarUrl = chat.chat_type === 'private'
    ? otherMember?.avatar_url || chat.avatar_url
    : chat.avatar_url
  const isOnline = otherMember && (
    presence[String(otherMember.user_id)]?.status === 'online' || otherMember.status === 'online'
  )

  return (
    <div onClick={onClick} className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-all border-l-2 ${isActive ? 'bg-dark-800 border-primary-500' : 'border-transparent hover:bg-dark-800/50'}`}>
      <div className="relative flex-shrink-0">
        <Avatar name={chatName} url={avatarUrl} size="md" />
        {isOnline && <span className="absolute bottom-0 right-0 w-3 h-3 rounded-full bg-green-500 border-2 border-dark-900" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between">
          <p className="font-medium text-white text-sm truncate flex items-center gap-1">{icon}{chatName}</p>
          {chat.last_message && <span className="text-xs text-dark-400 flex-shrink-0">{formatTime(chat.last_message.created_at)}</span>}
        </div>
        <div className="flex items-center justify-between mt-0.5">
          <p className="text-xs text-dark-400 truncate">
            {chat.last_message ? `${chat.last_message.sender_name}: ${chat.last_message.content || '📎 Файл'}` : 'Нет сообщений'}
          </p>
          {chat.unread_count > 0 && (
            <span className="ml-2 flex-shrink-0 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-primary-600 text-white text-[10px] font-bold rounded-full">{chat.unread_count}</span>
          )}
        </div>
      </div>
    </div>
  )
}

function getChatName(chat, currentUser) {
  if (chat.chat_type === 'saved') return 'Избранное'
  if (chat.is_news_channel) return chat.name || 'Новости ДГИ'
  if (chat.chat_type === 'private') {
    const other = chat.members?.find((m) => m.user_id !== currentUser?.id)
    return other ? `${other.first_name} ${other.last_name}` : 'Чат'
  }
  return chat.name || 'Групповой чат'
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const adjustedDate = new Date(date.getTime() + 3 * 60 * 60 * 1000)
  const now = new Date()
  const diff = now - adjustedDate
  if (diff < 86400000) return adjustedDate.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })
  return adjustedDate.toLocaleDateString('ru', { day: '2-digit', month: '2-digit' })
}
