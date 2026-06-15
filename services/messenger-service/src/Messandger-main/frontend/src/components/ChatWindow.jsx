import { useState, useRef, useEffect } from 'react'
import { Send, Paperclip, Smile, Phone, Video, X, BarChart3, UserPlus, Settings, Image, Mic, Clock, Square, CalendarClock, Search, FolderOpen, Lock, Radio } from 'lucide-react'
import EmojiPicker, { EmojiStyle, Theme as EmojiTheme } from 'emoji-picker-react'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import { useWebSocketStore } from '../store/websocketStore'
import { usePresenceStore, formatLastSeen } from '../store/presenceStore'
import { useThemeStore } from '../store/themeStore'
import { useCallStore } from '../store/callStore'
import Avatar from './Avatar'
import MessageBubble from './MessageBubble'
import PollModal from './PollModal'
import AddMembersModal from './AddMembersModal'
import ChatSettingsModal from './ChatSettingsModal'
import ImageEditorModal from './ImageEditorModal'
import ScheduledMessagesModal from './ScheduledMessagesModal'
import MediaGalleryModal from './MediaGalleryModal'
import api from '../api/axios'
import toast from 'react-hot-toast'
import { confirmDelete } from '../store/confirmStore'

export default function ChatWindow() {
  const { user } = useAuthStore()
  const { activeChat, messages, loadingMessages, sendMessage, editMessage, deleteMessage, typingUsers } = useChatStore()
  const { sendTyping, sendStopTyping, sendMessage: wsSendMessage, sendRead } = useWebSocketStore()
  const { broadcastInfo } = useCallStore()

  const [inputText, setInputText] = useState('')
  const [replyTo, setReplyTo] = useState(null)
  const [editingMessage, setEditingMessage] = useState(null)
  const [showPollModal, setShowPollModal] = useState(false)
  const [showAddMembers, setShowAddMembers] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [recording, setRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const [showSchedule, setShowSchedule] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  const [showScheduledList, setShowScheduledList] = useState(false)
  const [imageToEdit, setImageToEdit] = useState(null)
  const [showEmoji, setShowEmoji] = useState(false)
  const [allowDownload, setAllowDownload] = useState(true)
  const [showSearch, setShowSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [showMedia, setShowMedia] = useState(false)
  const [attachedFile, setAttachedFile] = useState(null)
  const [pendingFile, setPendingFile] = useState(null)
  const [showCaptionModal, setShowCaptionModal] = useState(false)
  const [fileCaption, setFileCaption] = useState('')
  const theme = useThemeStore((s) => s.theme)
  const messagesEndRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const typingTimeoutRef = useRef(null)
  const fileInputRef = useRef(null)
  const imageInputRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const recordingIntervalRef = useRef(null)
  const audioChunksRef = useRef([])

  const chatName = getChatDisplayName(activeChat, user)
  const memberIds = activeChat?.members?.map((m) => String(m.user_id)) || []
  const chatTypingUsers = typingUsers[activeChat?.id] || []
  const isReadonly = activeChat?.members?.find(m => m.user_id === user?.id)?.role === 'readonly'
  const myRole = activeChat?.members?.find(m => m.user_id === user?.id)?.role
  const isAdminOfChat = myRole === 'owner' || myRole === 'admin'
  const isSystemAdmin = user?.role === 'head' || user?.role === 'deputy_head' || user?.role === 'super_admin'
  const canDeleteOthers = isAdminOfChat || isSystemAdmin
  // В каналах (новостных каналах) обычные звонки недоступны.
  // Только владелец/админ канала может начать трансляцию.
  const isChannel = activeChat?.chat_type === 'channel' || activeChat?.is_news_channel
  const canStartCall = !isChannel
  const canBroadcast = isChannel && isAdminOfChat

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (activeChat) sendRead(activeChat.id, memberIds)
  }, [activeChat?.id])

  const handleTyping = () => {
    sendTyping(activeChat.id, memberIds)
    clearTimeout(typingTimeoutRef.current)
    typingTimeoutRef.current = setTimeout(() => sendStopTyping(activeChat.id, memberIds), 2000)
  }

  const handleSend = async () => {
    const text = inputText.trim()
    if (!text) return
    if (editingMessage) {
      await editMessage(activeChat.id, editingMessage.id, text)
      setEditingMessage(null)
    } else {
      const msg = await sendMessage(activeChat.id, text, replyTo?.id)
      if (msg) wsSendMessage(activeChat.id, msg, memberIds)
      setReplyTo(null)
    }
    setInputText('')
    sendStopTyping(activeChat.id, memberIds)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleFileUpload = async (e) => {
    const files = e.target.files
    if (!files || files.length === 0) return
    for (const file of files) {
      // Для изображений показываем модальное окно для подписи
      if (file.type.startsWith('image/')) {
        setPendingFile(file)
        setFileCaption('')
        setShowCaptionModal(true)
      } else {
        // Для остальных файлов загружаем сразу
        await uploadFile(file, null)
      }
    }
    e.target.value = ''
  }

  const uploadFile = async (file, caption) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('allow_download', allowDownload ? 'true' : 'false')
    if (caption && caption.trim()) {
      formData.append('content', caption.trim())
    }
    try {
      const res = await api.post(`/chats/${activeChat.id}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      useChatStore.setState((s) => ({ messages: [...s.messages, res.data] }))
      wsSendMessage(activeChat.id, res.data, memberIds)
      useChatStore.getState().fetchChats()
    } catch (err) {
      toast.error('Ошибка загрузки файла')
    }
  }

  const handleSendWithCaption = async () => {
    if (pendingFile) {
      await uploadFile(pendingFile, fileCaption)
      setPendingFile(null)
      setFileCaption('')
      setShowCaptionModal(false)
    }
  }

  const scrollToMessage = (id) => {
    const el = document.getElementById(`msg-${id}`)
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      el.classList.add('ring-2', 'ring-primary-500', 'rounded-xl', 'transition-all')
      setTimeout(() => el.classList.remove('ring-2', 'ring-primary-500'), 1500)
    }
  }

  const runSearch = async (q) => {
    setSearchQuery(q)
    if (!q.trim()) { setSearchResults([]); return }
    try {
      const res = await api.get(`/chats/${activeChat.id}/messages/search`, { params: { q } })
      setSearchResults(res.data)
    } catch {
      setSearchResults([])
    }
  }

  const handleStartCall = async (callType) => {
    try {
      // Защита: в каналах звонки запрещены
      if (isChannel && !canBroadcast) {
        return toast.error('В каналах звонки запрещены')
      }
      const otherMembers = memberIds.filter(id => id !== user?.id)
      const isBroadcast = isChannel
      
      // Для трансляций не требуются участники
      if (!isBroadcast && otherMembers.length === 0) return toast.error('Нет участников для звонка')
      
      const res = await api.post('/calls/', {
        chat_id: activeChat.id,
        call_type: callType,
        participant_ids: isBroadcast ? [] : otherMembers,
        is_broadcast: isBroadcast,
      })
      // Start WebRTC call via global handler
      if (window.__startCall) {
        window.__startCall(callType, isBroadcast ? [] : otherMembers, res.data.id, isBroadcast, activeChat.id)
      }
    } catch (err) {
      toast.error('Ошибка начала звонка')
    }
  }

  const handleJoinBroadcast = async () => {
    if (!broadcastInfo) return
    // Validate call_id before making API calls
    if (!broadcastInfo.call_id || broadcastInfo.call_id === 'undefined') {
      console.error('Invalid call_id in broadcastInfo:', broadcastInfo.call_id)
      toast.error('Ошибка: неверный ID трансляции')
      return
    }
    try {
      // Присоединиться к трансляции через API
      await api.post(`/calls/${broadcastInfo.call_id}/join`)

      // Получить информацию о ведущем
      const callerInfo = {
        user_id: broadcastInfo.from_user,
        first_name: broadcastInfo.from_name?.split(' ')[0] || 'Unknown',
        last_name: broadcastInfo.from_name?.split(' ')[1] || '',
        avatar_url: broadcastInfo.from_avatar || null,
      }

      const { setLocalStream, setActiveCall, setCallStatus, addPeerConnection } = useCallStore.getState()
      // Зрители не отправляют камеру/микрофон - только смотрят
      setLocalStream(null)
      setActiveCall({
        id: broadcastInfo.call_id,
        type: broadcastInfo.call_type,
        participants: [callerInfo],
        isOutgoing: false,
        isBroadcast: true
      })
      setCallStatus('active')

      // Создать peer connection с ведущим (без локальных треков)
      const ICE_SERVERS = [
        { urls: 'stun:stun.l.google.com:19302' },
        { urls: 'stun:stun1.l.google.com:19302' },
        { urls: 'stun:stun2.l.google.com:19302' },
      ]
      const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

      pc.onicecandidate = (event) => {
        if (event.candidate && useWebSocketStore.getState().ws?.readyState === WebSocket.OPEN) {
          useWebSocketStore.getState().ws.send(JSON.stringify({
            type: 'call_signal',
            call_id: broadcastInfo.call_id,
            signal_type: 'ice-candidate',
            signal: event.candidate,
            recipients: [broadcastInfo.from_user],
          }))
        }
      }

      pc.ontrack = (event) => {
        console.log('Received track from broadcaster:', event.streams[0])
        useCallStore.getState().addRemoteStream(broadcastInfo.from_user, event.streams[0])
      }

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === 'disconnected' || pc.connectionState === 'failed') {
          useCallStore.getState().removeRemoteStream(broadcastInfo.from_user)
        }
      }

      // Add recvonly transceivers for audio and video to receive broadcaster's stream
      pc.addTransceiver('audio', { direction: 'recvonly' })
      pc.addTransceiver('video', { direction: 'recvonly' })
      console.log('Added recvonly transceivers for audio and video')

      addPeerConnection(broadcastInfo.from_user, pc)

      // Запросить offer у ведущего
      useWebSocketStore.getState().ws.send(JSON.stringify({
        type: 'broadcast_join_request',
        call_id: broadcastInfo.call_id,
        from_user: user?.id,
        recipients: [broadcastInfo.from_user],
      }))

      // Очистить информацию о трансляции
      useCallStore.getState().setBroadcastInfo(null)
    } catch (err) {
      console.error('Join broadcast error:', err.name, err.message, err)
      let errorMsg = 'Не удалось присоединиться к трансляции'
      if (err.name === 'NotAllowedError') {
        errorMsg = 'Ошибка доступа'
      } else if (err.name === 'NotFoundError') {
        errorMsg = 'Трансляция не найдена'
      } else if (err.name === 'NotReadableError') {
        errorMsg = 'Ошибка соединения'
      } else if (err.name === 'OverconstrainedError') {
        errorMsg = 'Устройство не поддерживает запрошенные параметры'
      }
      toast.error(errorMsg)
    }
  }

  // Expose handleJoinBroadcast globally for system messages
  useEffect(() => {
    window.__joinBroadcast = handleJoinBroadcast
    return () => { delete window.__joinBroadcast }
  }, [handleJoinBroadcast, broadcastInfo])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const file = new File([blob], `voice_${Date.now()}.webm`, { type: 'audio/webm' })
        const formData = new FormData()
        formData.append('file', file)
        formData.append('allow_download', allowDownload ? 'true' : 'false')
        try {
          const res = await api.post(`/chats/${activeChat.id}/upload`, formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
          })
          useChatStore.setState((s) => ({ messages: [...s.messages, res.data] }))
          wsSendMessage(activeChat.id, res.data, memberIds)
          useChatStore.getState().fetchChats()
        } catch (err) {
          toast.error('Ошибка отправки голосового')
        }
      }

      mediaRecorder.start()
      setRecording(true)
      setRecordingTime(0)
      recordingIntervalRef.current = setInterval(() => setRecordingTime(t => t + 1), 1000)
    } catch (err) {
      toast.error('Нет доступа к микрофону')
    }
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    setRecording(false)
    clearInterval(recordingIntervalRef.current)
  }

  const cancelRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.ondataavailable = null
      mediaRecorderRef.current.onstop = null
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current.stream?.getTracks().forEach(t => t.stop())
    }
    setRecording(false)
    setRecordingTime(0)
    clearInterval(recordingIntervalRef.current)
  }

  const handleScheduleMessage = async () => {
    if (!inputText.trim() || !scheduleDate) return
    // datetime-local даёт локальную строку без TZ; конвертируем в UTC ISO,
    // чтобы backend (worker сравнивает по UTC) корректно сработал.
    const isoUtc = new Date(scheduleDate).toISOString()
    if (new Date(isoUtc).getTime() <= Date.now()) {
      toast.error('Время отправки должно быть в будущем')
      return
    }
    try {
      await api.post(`/chats/${activeChat.id}/messages/schedule`, {
        content: inputText.trim(),
        scheduled_at: isoUtc,
      })
      toast.success('Сообщение запланировано')
      setInputText('')
      setShowSchedule(false)
      setScheduleDate('')
    } catch (err) {
      toast.error('Ошибка планирования')
    }
  }

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type.startsWith('image/')) {
      const reader = new FileReader()
      reader.onload = (ev) => setImageToEdit({ dataUrl: ev.target.result, file })
      reader.readAsDataURL(file)
    }
    e.target.value = ''
  }

  const handleImageEditorSave = async (editedBlob) => {
    const file = new File([editedBlob], imageToEdit.file.name || 'image.png', { type: editedBlob.type || 'image/png' })
    const formData = new FormData()
    formData.append('file', file)
    formData.append('allow_download', allowDownload ? 'true' : 'false')
    try {
      const res = await api.post(`/chats/${activeChat.id}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      useChatStore.setState((s) => ({ messages: [...s.messages, res.data] }))
      wsSendMessage(activeChat.id, res.data, memberIds)
      useChatStore.getState().fetchChats()
    } catch (err) {
      toast.error('Ошибка загрузки')
    }
    setImageToEdit(null)
  }

  const formatRecordTime = (s) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`

  return (
    <div className="flex-1 flex flex-col bg-dark-900 relative">
      {/* Hidden file input */}
      <input type="file" ref={fileInputRef} className="hidden" multiple onChange={handleFileUpload} accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.xls,.xlsx,.zip,.rar,.txt" />

      {/* Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-dark-700 bg-dark-900/95 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <Avatar name={chatName} url={activeChat.chat_type === 'private' ? activeChat.members?.find(m => m.user_id !== user?.id)?.avatar_url || activeChat.avatar_url : activeChat.avatar_url} size="md" />
          <div className="min-w-0">
            <h3 className="font-heading font-semibold text-white text-sm truncate">{chatName}</h3>
            <ChatSubtitle chat={activeChat} userId={user?.id} />
          </div>
        </div>
        {activeChat.chat_type !== 'saved' && (
          <div className="flex items-center gap-1">
            <button onClick={() => setShowSearch(v => !v)} className={`p-2 rounded-lg transition-colors ${showSearch ? 'bg-primary-600/30 text-primary-300' : 'hover:bg-dark-700 text-dark-400 hover:text-white'}`} title="Поиск по чату"><Search size={18} /></button>
            <button onClick={() => setShowMedia(true)} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Файлы и медиа"><FolderOpen size={18} /></button>
            <button onClick={() => setShowScheduledList(true)} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Запланированные"><CalendarClock size={18} /></button>
            {canStartCall && (
              <>
                <button onClick={() => handleStartCall('audio')} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Аудиозвонок"><Phone size={18} /></button>
                <button onClick={() => handleStartCall('video')} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Видеозвонок"><Video size={18} /></button>
              </>
            )}
            {canBroadcast && (
              <button
                onClick={() => handleStartCall('video')}
                className="px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-400 hover:text-red-300 text-xs font-medium flex items-center gap-1.5 transition-colors"
                title="Начать прямую трансляцию для подписчиков канала"
              >
                <Radio size={14} className="animate-pulse" /> Трансляция
              </button>
            )}
            {isAdminOfChat && activeChat.chat_type !== 'private' && (
              <button onClick={() => setShowAddMembers(true)} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Добавить участников"><UserPlus size={18} /></button>
            )}
            {activeChat.chat_type !== 'private' && (
              <button onClick={() => setShowSettings(true)} className="p-2 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white transition-colors" title="Настройки"><Settings size={18} /></button>
            )}
          </div>
        )}
      </div>

      {/* Search bar */}
      {showSearch && (
        <div className="px-4 py-2 border-b border-dark-700 bg-dark-800/50 flex flex-col gap-2">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
            <input
              type="text"
              autoFocus
              value={searchQuery}
              onChange={(e) => runSearch(e.target.value)}
              placeholder="Найти в этом чате..."
              className="w-full pl-9 pr-9 py-2 bg-dark-700 border border-dark-600 rounded-xl text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
            <button onClick={() => { setShowSearch(false); setSearchQuery(''); setSearchResults([]) }} className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-dark-400 hover:text-white"><X size={14} /></button>
          </div>
          {searchResults.length > 0 && (
            <div className="max-h-40 overflow-y-auto space-y-1">
              {searchResults.map((r) => (
                <button
                  key={r.id}
                  onClick={() => { scrollToMessage(r.id); setShowSearch(false) }}
                  className="w-full text-left bg-dark-800 hover:bg-dark-700 rounded-lg px-3 py-1.5"
                >
                  <p className="text-[10px] text-primary-400">{r.sender_name} · {new Date(new Date(r.created_at).getTime() + 3 * 60 * 60 * 1000).toLocaleString('ru')}</p>
                  <p className="text-xs text-white truncate">{r.content}</p>
                </button>
              ))}
            </div>
          )}
          {searchQuery && searchResults.length === 0 && (
            <p className="text-xs text-dark-400 text-center py-1">Ничего не найдено</p>
          )}
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1">
        {/* Broadcast join banner */}
        {isChannel && broadcastInfo && (!broadcastInfo.chat_id || broadcastInfo.chat_id === activeChat?.id) && (
          <div className="mb-4 bg-gradient-to-r from-red-600/20 to-orange-600/20 border border-red-500/30 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-600/30 flex items-center justify-center">
                <Radio size={20} className="text-red-400 animate-pulse" />
              </div>
              <div>
                <p className="text-white font-medium text-sm">Идет трансляция</p>
                <p className="text-dark-400 text-xs">{broadcastInfo.from_name} начал{broadcastInfo.call_type === 'video' ? ' видеотрансляцию' : ' аудиотрансляцию'}</p>
              </div>
            </div>
            <button
              onClick={handleJoinBroadcast}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2"
            >
              <Video size={16} /> Присоединиться
            </button>
          </div>
        )}
        {loadingMessages ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full" />
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => {
              const isMine = msg.sender_id === user?.id
              const showDate = idx === 0 || !isSameDay(messages[idx - 1].created_at, msg.created_at)
              return (
                <div key={msg.id}>
                  {showDate && <DateSeparator date={msg.created_at} />}
                  <MessageBubble msg={msg} isMine={isMine} chatId={activeChat.id} canDeleteOthers={canDeleteOthers}
                    onReply={(m) => setReplyTo(m)}
                    onReplyClick={scrollToMessage}
                    onEdit={(m) => { setEditingMessage(m); setInputText(m.content || '') }}
                    onDelete={async (m) => {
                      if (await confirmDelete('Удалить это сообщение? Действие нельзя отменить.')) {
                        deleteMessage(activeChat.id, m.id)
                      }
                    }}
                  />
                </div>
              )
            })}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Typing (фильтруем сами себя) */}
      {chatTypingUsers.filter((uid) => uid !== user?.id).length > 0 && (
        <div className="px-4 py-1">
          <p className="text-xs text-primary-400 animate-pulse">{typingLabel(chatTypingUsers, user, activeChat)}</p>
        </div>
      )}

      {/* Reply / Edit bar */}
      {(replyTo || editingMessage) && (
        <div className="px-4 py-2 bg-dark-800 border-t border-dark-700 flex items-center gap-3">
          <div className="w-1 h-8 bg-primary-500 rounded-full" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-primary-400 font-medium">{editingMessage ? 'Редактирование' : `Ответ: ${replyTo?.sender_name}`}</p>
            <p className="text-xs text-dark-400 truncate">{editingMessage?.content || replyTo?.content}</p>
          </div>
          <button onClick={() => { setReplyTo(null); setEditingMessage(null); setInputText('') }} className="p-1 text-dark-400 hover:text-white" title="Отменить"><X size={16} /></button>
        </div>
      )}

      {/* Schedule bar */}
      {showSchedule && (
        <div className="px-4 py-2 bg-dark-800 border-t border-dark-700 flex items-center gap-3">
          <Clock size={14} className="text-orange-400" />
          <input type="datetime-local" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)} className="bg-dark-700 border border-dark-600 rounded-lg px-3 py-1 text-sm text-white focus:outline-none focus:ring-1 focus:ring-primary-500" />
          <button onClick={handleScheduleMessage} disabled={!inputText.trim() || !scheduleDate} className="px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white text-xs rounded-lg disabled:opacity-40">Запланировать</button>
          <button onClick={() => setShowSchedule(false)} className="p-1 text-dark-400 hover:text-white" title="Закрыть"><X size={14} /></button>
        </div>
      )}

      {/* Recording bar */}
      {recording && (
        <div className="px-4 py-3 border-t border-red-500/20 bg-dark-800 flex items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-pulse shadow-lg shadow-red-500/30" />
            <span className="text-base text-red-400 font-mono font-medium tracking-wider">{formatRecordTime(recordingTime)}</span>
          </div>
          <div className="flex-1 flex items-center gap-0.5 justify-center">
            {Array.from({ length: 30 }).map((_, i) => (
              <div key={i} className="w-[2px] bg-red-400/50 rounded-full animate-pulse" style={{ height: `${4 + Math.random() * 16}px`, animationDelay: `${i * 50}ms` }} />
            ))}
          </div>
          <div className="flex gap-2">
            <button onClick={cancelRecording} className="px-4 py-2 bg-dark-700 text-dark-300 text-xs rounded-xl hover:bg-dark-600 transition-colors font-medium" title="Отменить запись">Отмена</button>
            <button onClick={stopRecording} className="px-4 py-2 bg-red-600 text-white text-xs rounded-xl hover:bg-red-700 flex items-center gap-1.5 transition-colors font-medium shadow-lg shadow-red-500/20" title="Остановить и отправить"><Square size={10} /> Отправить</button>
          </div>
        </div>
      )}

      {/* Input */}
      {!isReadonly && !recording && (
        <div className="px-4 py-3 border-t border-dark-700 bg-dark-900 flex-shrink-0 relative">
          {/* Allow-download toggle for attachments */}
          <div className="flex items-center justify-end gap-1 mb-1.5">
            <label className="flex items-center gap-1.5 text-[11px] text-dark-400 cursor-pointer select-none hover:text-dark-200 transition-colors">
              <input
                type="checkbox"
                checked={allowDownload}
                onChange={(e) => setAllowDownload(e.target.checked)}
                className="w-3 h-3 accent-primary-600"
              />
              {allowDownload ? 'Разрешить скачивание вложений' : <span className="inline-flex items-center gap-1 text-primary-400"><Lock size={10} /> Скачивание запрещено</span>}
            </label>
          </div>
          {showEmoji && (
            <div className="absolute bottom-full right-2 mb-2 z-30 shadow-2xl rounded-2xl overflow-hidden">
              <EmojiPicker
                onEmojiClick={(d) => { setInputText((t) => t + d.emoji); setShowEmoji(false) }}
                theme={theme === 'light' ? EmojiTheme.LIGHT : EmojiTheme.DARK}
                emojiStyle={EmojiStyle.NATIVE}
                lazyLoadEmojis
                searchPlaceHolder="Поиск эмодзи..."
                width={320}
                height={400}
              />
            </div>
          )}
          <div className="flex items-end gap-1.5">
            <button onClick={() => fileInputRef.current?.click()} className="p-2 rounded-xl hover:bg-dark-700 text-dark-400 hover:text-white transition-colors flex-shrink-0" title="Прикрепить файл">
              <Paperclip size={18} />
            </button>
            <button onClick={() => imageInputRef.current?.click()} className="p-2 rounded-xl hover:bg-dark-700 text-dark-400 hover:text-white transition-colors flex-shrink-0" title="Фото с редактором">
              <Image size={18} />
            </button>
            <input type="file" ref={imageInputRef} className="hidden" accept="image/*" onChange={handleImageSelect} />
            <button onClick={() => setShowEmoji(v => !v)} className={`p-2 rounded-xl transition-colors flex-shrink-0 ${showEmoji ? 'bg-primary-600/30 text-primary-300' : 'hover:bg-dark-700 text-dark-400 hover:text-white'}`} title="Эмодзи">
              <Smile size={18} />
            </button>
            {activeChat.chat_type !== 'saved' && (
              <>
                <button onClick={() => setShowPollModal(true)} className="p-2 rounded-xl hover:bg-dark-700 text-dark-400 hover:text-white transition-colors flex-shrink-0" title="Опрос">
                  <BarChart3 size={18} />
                </button>
                <button onClick={() => setShowSchedule(!showSchedule)} className="p-2 rounded-xl hover:bg-dark-700 text-dark-400 hover:text-white transition-colors flex-shrink-0" title="Запланировать">
                  <Clock size={18} />
                </button>
              </>
            )}
            <textarea value={inputText} onChange={(e) => { setInputText(e.target.value); handleTyping() }} onKeyDown={handleKeyDown}
              className="flex-1 px-4 py-2.5 bg-dark-800 border border-dark-600 rounded-xl text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none text-sm"
              placeholder="Введите сообщение..." rows={1} style={{ maxHeight: '120px' }} />
            {inputText.trim() ? (
              <button onClick={handleSend} className="p-2.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white transition-colors flex-shrink-0" title="Отправить">
                <Send size={18} />
              </button>
            ) : (
              <button onClick={startRecording} className="p-2.5 rounded-xl hover:bg-dark-700 text-dark-400 hover:text-red-400 transition-colors flex-shrink-0" title="Голосовое сообщение">
                <Mic size={18} />
              </button>
            )}
          </div>
        </div>
      )}

      {isReadonly && !recording && (
        <div className="px-4 py-3 border-t border-dark-700 bg-dark-800 text-center">
          <p className="text-dark-400 text-sm">Только для чтения</p>
        </div>
      )}

      {showPollModal && <PollModal chatId={activeChat.id} onClose={() => setShowPollModal(false)} />}
      {showAddMembers && <AddMembersModal chatId={activeChat.id} onClose={() => setShowAddMembers(false)} />}
      {showSettings && <ChatSettingsModal chat={activeChat} onClose={() => setShowSettings(false)} />}
      {imageToEdit && <ImageEditorModal imageData={imageToEdit.dataUrl} onSave={handleImageEditorSave} onClose={() => setImageToEdit(null)} />}
      {showScheduledList && <ScheduledMessagesModal chatId={activeChat.id} onClose={() => setShowScheduledList(false)} />}
      {showMedia && <MediaGalleryModal chatId={activeChat.id} title={`Файлы и медиа · ${chatName}`} onClose={() => setShowMedia(false)} />}
      {showCaptionModal && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center">
          <div className="bg-dark-900 border border-dark-700 rounded-2xl p-6 max-w-md w-full mx-4 shadow-2xl">
            <h3 className="text-white font-bold text-lg mb-4">Добавить подпись к фото</h3>
            {pendingFile && (
              <div className="mb-4">
                <img 
                  src={URL.createObjectURL(pendingFile)} 
                  alt="Preview" 
                  className="w-full h-48 object-cover rounded-lg"
                />
              </div>
            )}
            <textarea
              value={fileCaption}
              onChange={(e) => setFileCaption(e.target.value)}
              placeholder="Введите подпись к фото..."
              className="w-full px-4 py-3 bg-dark-800 border border-dark-600 rounded-xl text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500 resize-none text-sm"
              rows={3}
            />
            <div className="flex items-center justify-end gap-3 mt-4">
              <button
                onClick={() => { setShowCaptionModal(false); setPendingFile(null); setFileCaption('') }}
                className="px-4 py-2 rounded-lg bg-dark-700 hover:bg-dark-600 text-white text-sm font-medium transition-colors"
              >
                Отмена
              </button>
              <button
                onClick={handleSendWithCaption}
                className="px-4 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium transition-colors"
              >
                Отправить
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ChatSubtitle({ chat, userId }) {
  const presence = usePresenceStore((s) => s.presence)
  if (!chat) return null
  if (chat.chat_type === 'saved') return <p className="text-xs text-dark-400">Ваши заметки и файлы</p>
  if (chat.is_news_channel) return <p className="text-xs text-dark-400">Новостной канал</p>
  if (chat.chat_type === 'private') {
    const other = chat.members?.find((m) => m.user_id !== userId)
    if (!other) return <p className="text-xs text-dark-400">Личный чат</p>
    const p = presence[String(other.user_id)]
    const online = p?.status === 'online' || other.status === 'online'
    if (online) return <p className="text-xs text-green-400 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" /> в сети</p>
    return <p className="text-xs text-dark-400">{formatLastSeen(p?.last_seen || other.last_seen)}</p>
  }
  return <p className="text-xs text-dark-400">{chat.members?.length || 0} участников</p>
}

function typingLabel(typingIds, currentUser, chat) {
  const ids = typingIds.filter((uid) => uid !== currentUser?.id)
  if (ids.length === 0) return ''
  const m = (uid) => {
    const mem = chat?.members?.find((x) => String(x.user_id) === String(uid))
    return mem ? `${mem.first_name} ${mem.last_name}` : 'кто-то'
  }
  if (ids.length === 1) return `${m(ids[0])} печатает...`
  if (ids.length === 2) return `${m(ids[0])} и ${m(ids[1])} печатают...`
  return 'Несколько участников печатают...'
}

function getChatDisplayName(chat, currentUser) {
  if (chat?.chat_type === 'saved') return 'Избранное'
  if (chat?.is_news_channel) return chat?.name || 'Новости ДГИ'
  if (chat?.chat_type === 'private') {
    const other = chat.members?.find((m) => m.user_id !== currentUser?.id)
    return other ? `${other.first_name} ${other.last_name}` : 'Чат'
  }
  return chat?.name || 'Групповой чат'
}

function DateSeparator({ date }) {
  const d = new Date(date)
  const adjustedD = new Date(d.getTime() + 3 * 60 * 60 * 1000)
  const today = new Date()
  const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1)
  let label
  if (adjustedD.toDateString() === today.toDateString()) label = 'Сегодня'
  else if (adjustedD.toDateString() === yesterday.toDateString()) label = 'Вчера'
  else label = adjustedD.toLocaleDateString('ru', { day: 'numeric', month: 'long', year: 'numeric' })
  return (
    <div className="flex items-center justify-center my-3">
      <span className="px-3 py-1 bg-dark-800 rounded-full text-xs text-dark-400">{label}</span>
    </div>
  )
}

function isSameDay(d1, d2) {
  return new Date(d1).toDateString() === new Date(d2).toDateString()
}
