import { useState, useRef } from 'react'
import { X, Settings, Trash2, LogOut, Snowflake, Camera, Upload } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import Avatar from './Avatar'
import { confirmDelete } from '../store/confirmStore'

export default function ChatSettingsModal({ chat, onClose }) {
  const [name, setName] = useState(chat.name || '')
  const [description, setDescription] = useState(chat.description || '')
  const [showDeletedLabel, setShowDeletedLabel] = useState(chat.show_deleted_label !== false)
  const [avatarUrl, setAvatarUrl] = useState(chat.avatar_url || null)
  const avatarInputRef = useRef(null)
  const { fetchChats } = useChatStore()
  const { user } = useAuthStore()

  const handleSave = async () => {
    try {
      await api.put(`/chats/${chat.id}/settings`, {
        name: name.trim(),
        description: description.trim(),
        show_deleted_label: showDeletedLabel,
      })
      toast.success('Настройки сохранены')
      fetchChats()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleRemoveMember = async (userId, memberName) => {
    if (!(await confirmDelete(`Удалить «${memberName}» из чата?`))) return
    try {
      await api.delete(`/chats/${chat.id}/members/${userId}`)
      toast.success('Участник удалён')
      fetchChats()
    } catch (e) {
      toast.error('Ошибка')
    }
  }

  const handleLeaveChat = async () => {
    if (!(await confirmDelete(`Выйти из «${chat.name}»?`))) return
    try {
      await api.post(`/chats/${chat.id}/leave`)
      toast.success('Вы вышли из чата')
      fetchChats()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleDeleteChat = async () => {
    if (!(await confirmDelete(`Удалить «${chat.name}»? Это действие нельзя отменить.`))) return
    try {
      await api.delete(`/chats/${chat.id}`)
      toast.success('Чат удалён')
      fetchChats()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleFreezeChat = async () => {
    try {
      const res = await api.post(`/chats/${chat.id}/freeze`)
      toast.success(res.data.message)
      fetchChats()
      onClose()
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    }
  }

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      toast.error('Только изображения')
      return
    }
    const formData = new FormData()
    formData.append('file', file)
    try {
      console.log('Uploading avatar for chat:', chat.id)
      const res = await api.post(`/chats/${chat.id}/avatar/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setAvatarUrl(res.data.avatar_url)
      toast.success('Аватар обновлен')
      fetchChats()
    } catch (e) {
      console.error('Avatar upload error:', e)
      toast.error(e.response?.data?.detail || 'Ошибка загрузки аватара')
    }
    e.target.value = ''
  }

  const handleAvatarDelete = async () => {
    if (!(await confirmDelete('Удалить аватар чата?'))) return
    try {
      await api.delete(`/chats/${chat.id}/avatar`)
      setAvatarUrl(null)
      toast.success('Аватар удален')
      fetchChats()
    } catch (e) {
      toast.error('Ошибка удаления аватара')
    }
  }

  // Check if current user is owner
  const myMember = chat.members?.find(m => String(m.user_id) === String(user?.id))
  const isOwner = myMember?.role === 'owner'
  const isSuperAdmin = user?.role === 'super_admin'
  const canLeave = chat.chat_type !== 'private' && !isOwner && !(chat.is_news_channel && chat.name === 'Новости ДГИ') && myMember
  const canDelete = (chat.chat_type !== 'private' && isOwner && !(chat.is_news_channel && chat.name === 'Новости ДГИ')) || 
                    (isSuperAdmin && chat.chat_type !== 'private' && !(chat.is_news_channel && chat.name === 'Новости ДГИ'))
  const canFreeze = isSuperAdmin && chat.chat_type !== 'private' && !(chat.is_news_channel && chat.name === 'Новости ДГИ')

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="text-lg font-bold text-white flex items-center gap-2"><Settings size={20} className="text-primary-400" /> Настройки чата</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-4 space-y-4 overflow-y-auto">
          {/* Avatar section */}
          {chat.chat_type !== 'private' && (
            <div className="flex items-center gap-4">
              <div className="relative">
                <Avatar name={chat.name} url={avatarUrl} size="lg" />
                <button
                  onClick={() => avatarInputRef.current?.click()}
                  className="absolute -bottom-1 -right-1 w-8 h-8 bg-primary-600 hover:bg-primary-700 rounded-full flex items-center justify-center text-white shadow-lg"
                  title="Загрузить аватар"
                >
                  <Camera size={14} />
                </button>
                <input
                  type="file"
                  ref={avatarInputRef}
                  className="hidden"
                  accept="image/*"
                  onChange={handleAvatarUpload}
                />
              </div>
              <div className="flex-1">
                <p className="text-sm text-white font-medium">Аватар чата</p>
                <p className="text-xs text-dark-400">PNG, JPG до {10} МБ</p>
              </div>
              {avatarUrl && (
                <button
                  onClick={handleAvatarDelete}
                  className="p-2 text-dark-400 hover:text-red-400 transition-colors"
                  title="Удалить аватар"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-dark-300 mb-1">Название</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-dark-300 mb-1">Описание</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="input-field" rows={2} />
          </div>

          {chat.chat_type === 'group' && (
            <div>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={showDeletedLabel} onChange={(e) => setShowDeletedLabel(e.target.checked)} className="w-4 h-4 rounded accent-primary-600" />
                <span className="text-sm text-dark-300">Показывать «Сообщение удалено»</span>
              </label>
              <p className="text-xs text-dark-500 mt-1">Если выключено — удалённые сообщения исчезают бесследно</p>
            </div>
          )}

          {/* Members list */}
          <div>
            <label className="block text-xs font-medium text-dark-300 mb-2">Участники ({chat.members?.length})</label>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {chat.members?.map((m) => (
                <div key={m.user_id} className="flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-dark-800">
                  <div className="flex items-center gap-2">
                    <Avatar name={m.first_name} url={m.avatar_url} size="sm" />
                    <div>
                      <p className="text-xs text-white">{m.first_name} {m.last_name}</p>
                      <p className="text-[10px] text-dark-400">{m.role === 'owner' ? 'Владелец' : m.role === 'admin' ? 'Админ' : m.role === 'readonly' ? 'Только чтение' : 'Участник'}</p>
                    </div>
                  </div>
                  {m.role !== 'owner' && (
                    <button onClick={() => handleRemoveMember(m.user_id, `${m.first_name} ${m.last_name}`)} className="p-1 text-dark-400 hover:text-red-400"><Trash2 size={14} /></button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Leave chat button for non-owners */}
          {canLeave && (
            <button onClick={handleLeaveChat} className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2">
              <LogOut size={16} /> Выйти из чата
            </button>
          )}

          {/* Delete chat button for owners and super_admin */}
          {canDelete && (
            <button onClick={handleDeleteChat} className="w-full py-2.5 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2">
              <Trash2 size={16} /> Удалить чат
            </button>
          )}

          {/* Freeze chat button for super_admin */}
          {canFreeze && (
            <button onClick={handleFreezeChat} className={`w-full py-2.5 text-white text-sm font-medium rounded-xl flex items-center justify-center gap-2 ${chat.is_frozen ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'}`}>
              <Snowflake size={16} /> {chat.is_frozen ? 'Разморозить чат' : 'Заморозить чат'}
            </button>
          )}

          <button onClick={handleSave} className="btn-primary w-full">Сохранить</button>
        </div>
      </div>
    </div>
  )
}
