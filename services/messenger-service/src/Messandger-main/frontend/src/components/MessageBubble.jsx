import { useState, useRef } from 'react'
import { Reply, Pencil, Trash2, MoreHorizontal, Smile, Play, Pause, FileText, Download, Mic, Check, CheckCheck, Clock, Forward, Copy, Lock, Music } from 'lucide-react'
import api from '../api/axios'
import PollMessage from './PollMessage'
import ForwardMessageModal from './ForwardMessageModal'
import { useLightboxStore } from '../store/lightboxStore'
import toast from 'react-hot-toast'

const QUICK_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥', '👏', '🎉']

export default function MessageBubble({ msg, isMine, onReply, onEdit, onDelete, onReplyClick, chatId, canDeleteOthers = false }) {
  const [showMenu, setShowMenu] = useState(false)
  const [showEmojiPicker, setShowEmojiPicker] = useState(false)
  const [playing, setPlaying] = useState(false)
  const [voiceProgress, setVoiceProgress] = useState(0)
  const [voiceDuration, setVoiceDuration] = useState(0)
  const [voiceCurrentTime, setVoiceCurrentTime] = useState(0)
  const [showForward, setShowForward] = useState(false)
  const audioRef = useRef(null)
  const [localReactions, setLocalReactions] = useState(msg.reactions || [])
  const showLightbox = useLightboxStore((s) => s.show)

  if (msg.is_deleted) {
    return (
      <div className={`flex ${isMine ? 'justify-end' : 'justify-start'} mb-1`}>
        <div className="px-3 py-2 rounded-2xl bg-dark-800/50 italic text-dark-500 text-xs">Сообщение удалено</div>
      </div>
    )
  }

  if (msg.is_system || msg.message_type === 'system') {
    const isBroadcast = (msg.content || '').includes('трансляция')
    return (
      <div className="flex justify-center mb-2">
        <div
          className={`px-4 py-2 rounded-full text-xs cursor-pointer transition-colors ${
            isBroadcast
              ? 'bg-red-600/20 text-red-400 hover:bg-red-600/30'
              : 'bg-dark-800/50 text-dark-400'
          }`}
          onClick={() => {
            if (isBroadcast && window.__joinBroadcast) {
              window.__joinBroadcast()
            }
          }}
        >
          {isBroadcast ? '📡 Нажмите, чтобы присоединиться к трансляции' : msg.content}
        </div>
      </div>
    )
  }

  const time = new Date(new Date(msg.created_at).getTime() + 3 * 60 * 60 * 1000).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })

  const handleReaction = async (emoji) => {
    try {
      const res = await api.post(`/chats/${chatId}/messages/${msg.id}/reactions`, { emoji })
      if (res.data.action === 'added') {
        setLocalReactions((prev) => [...prev, { emoji, user_id: 'me', id: res.data.id }])
      } else {
        setLocalReactions((prev) => {
          const idx = prev.findIndex((r) => r.emoji === emoji)
          if (idx >= 0) return [...prev.slice(0, idx), ...prev.slice(idx + 1)]
          return prev
        })
      }
    } catch (e) {}
    setShowEmojiPicker(false)
  }

  const handleCopy = async () => {
    try {
      const txt = msg.content || ''
      if (!txt) {
        toast('Нечего копировать')
      } else {
        await navigator.clipboard.writeText(txt)
        toast.success('Скопировано')
      }
    } catch {
      toast.error('Не удалось скопировать')
    }
    setShowMenu(false)
  }

  const isVoice = msg.message_type === 'voice'
  const isPoll = msg.message_type === 'poll'
  const allowDownload = msg.allow_download !== false
  const isForwarded = !!msg.forwarded_from_id

  return (
    <div id={`msg-${msg.id}`} className={`flex ${isMine ? 'justify-end' : 'justify-start'} group mb-1`} onMouseLeave={() => { setShowMenu(false); setShowEmojiPicker(false) }}>
      <div className={`max-w-[70%] relative ${isMine ? 'order-2' : ''}`}>
        {/* Sender name for groups */}
        {!isMine && msg.sender_name && (
          <p className="text-xs text-primary-400 font-medium mb-0.5 ml-1">{msg.sender_name}</p>
        )}

        {/* Reply preview — clickable */}
        {msg.reply_to && (
          <button
            type="button"
            onClick={() => onReplyClick?.(msg.reply_to.id)}
            className={`block w-full ml-1 mb-1 pl-2 pr-2 py-1 border-l-2 border-primary-500 text-left rounded-r-md hover:bg-dark-800/50 transition-colors ${isMine ? 'border-primary-300' : ''}`}
            title="Перейти к исходному сообщению"
          >
            <p className="text-[10px] text-primary-400 font-medium">{msg.reply_to.sender_name}</p>
            <p className="text-[11px] text-dark-300 truncate">{msg.reply_to.content || '[вложение]'}</p>
          </button>
        )}

        <div className={`${isMine ? 'chat-bubble-sent' : 'chat-bubble-received'} relative`}>
          {isForwarded && (
            <div className="flex items-center gap-1 text-[10px] mb-1 opacity-80">
              <Forward size={10} /> Переслано
            </div>
          )}

          {/* Attachments (skip for voice — rendered by custom waveform below) */}
          {!isVoice && msg.attachments?.length > 0 && (
            <div className="mb-1 space-y-1">
              {msg.attachments.map((a) => (
                <div key={a.id}>
                  {a.file_type?.startsWith('image') ? (
                    <img
                      src={a.file_url}
                      alt={a.file_name}
                      className="rounded-lg w-full max-h-80 object-cover cursor-pointer hover:opacity-90"
                      onClick={() => showLightbox(a.file_url, a.file_name, allowDownload)}
                    />
                  ) : a.file_type?.startsWith('video') ? (
                    <video src={a.file_url} controls controlsList={allowDownload ? '' : 'nodownload'} className="rounded-lg max-h-48 w-full" />
                  ) : a.file_type?.startsWith('audio') ? (
                    <div className="flex items-center gap-3 bg-dark-800 rounded-xl p-3 min-w-[240px] max-w-[320px]">
                      <button onClick={() => {
                        const audio = audioRef.current
                        if (!audio) return
                        if (playing) { audio.pause() } else { audio.play() }
                        setPlaying(!playing)
                      }} className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${playing ? 'bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/20' : isMine ? 'bg-white/20 hover:bg-white/30' : 'bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-500/20'}`} title={playing ? 'Пауза' : 'Воспроизвести'}>
                        {playing ? <Pause size={16} className="text-white" /> : <Play size={16} className="text-white ml-0.5" />}
                      </button>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-white truncate mb-1">{a.file_name}</p>
                        <div className="h-1 bg-dark-700 rounded-full overflow-hidden">
                          <div className="h-full bg-primary-500 transition-all duration-100" style={{ width: voiceProgress > 0 ? `${voiceProgress * 100}%` : '0%' }} />
                        </div>
                      </div>
                      <Music size={14} className={isMine ? 'text-primary-200' : 'text-dark-500'} flex-shrink-0 />
                      <audio ref={audioRef} src={a.file_url} onTimeUpdate={(e) => {
                        const audio = e.target
                        if (audio.duration) {
                          setVoiceProgress(audio.currentTime / audio.duration)
                          setVoiceCurrentTime(audio.currentTime)
                          setVoiceDuration(audio.duration)
                        }
                      }} onEnded={() => { setPlaying(false); setVoiceProgress(0) }} className="hidden" />
                    </div>
                  ) : (
                    <FileAttachment a={a} allowDownload={allowDownload} />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Voice message — custom waveform */}
          {isVoice && msg.attachments?.[0] && (
            <div className="flex items-center gap-3 min-w-[220px] max-w-[280px]">
              <button onClick={() => {
                const audio = audioRef.current
                if (!audio) return
                if (playing) { audio.pause() } else { audio.play() }
                setPlaying(!playing)
              }} className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 transition-all ${playing ? 'bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/20' : isMine ? 'bg-white/20 hover:bg-white/30' : 'bg-primary-600 hover:bg-primary-700 shadow-lg shadow-primary-500/20'}`} title={playing ? 'Пауза' : 'Воспроизвести'}>
                {playing ? <Pause size={16} className="text-white" /> : <Play size={16} className="text-white ml-0.5" />}
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1 mb-1.5">
                  {Array.from({ length: 20 }).map((_, i) => {
                    const h = Math.sin(i * 0.8 + (msg.id?.charCodeAt?.(0) || 0)) * 0.5 + 0.5
                    const filled = voiceDuration > 0 ? (i / 20) <= voiceProgress : false
                    return <div key={i} className={`w-[3px] rounded-full transition-all duration-100 ${filled ? (isMine ? 'bg-white' : 'bg-primary-400') : (isMine ? 'bg-white/25' : 'bg-dark-500')}`} style={{ height: `${8 + h * 14}px` }} />
                  })}
                </div>
                <div className="flex items-center justify-between">
                  <span className={`text-[10px] font-mono ${isMine ? 'text-primary-100' : 'text-dark-400'}`}>
                    {playing ? formatVoiceTime(voiceCurrentTime) : formatVoiceTime(voiceDuration)}
                  </span>
                  <Mic size={10} className={isMine ? 'text-primary-200' : 'text-dark-500'} />
                </div>
              </div>
              <audio
                ref={audioRef}
                src={msg.attachments[0].file_url}
                onLoadedMetadata={(e) => setVoiceDuration(e.target.duration || 0)}
                onTimeUpdate={(e) => {
                  setVoiceCurrentTime(e.target.currentTime)
                  setVoiceProgress(e.target.duration ? e.target.currentTime / e.target.duration : 0)
                }}
                onEnded={() => { setPlaying(false); setVoiceProgress(0); setVoiceCurrentTime(0) }}
                className="hidden"
              />
            </div>
          )}

          {isPoll && msg.poll && <PollMessage poll={msg.poll} isMine={isMine} />}

          {msg.content && !isVoice && !isPoll && (
            <p className="text-sm whitespace-pre-wrap break-words">{renderContent(msg.content)}</p>
          )}

          <div className="flex items-center justify-end gap-1 mt-0.5">
            {!allowDownload && msg.attachments?.length > 0 && (
              <Lock size={9} className={isMine ? 'text-primary-200/80' : 'text-dark-400'} aria-label="Скачивание запрещено" />
            )}
            {msg.is_edited && <span className="text-[10px] text-dark-400 italic">ред.</span>}
            <span className={`text-[10px] ${isMine ? 'text-primary-200' : 'text-dark-400'}`}>{time}</span>
            {isMine && <MessageStatus msg={msg} />}
          </div>
        </div>

        {/* Reactions */}
        {localReactions.length > 0 && (
          <div className="flex gap-0.5 mt-0.5 flex-wrap">
            {groupReactions(localReactions).map(([emoji, count]) => (
              <button key={emoji} onClick={() => handleReaction(emoji)} className="bg-dark-800 border border-dark-600 rounded-full px-1.5 py-0.5 text-xs hover:bg-dark-700 transition-colors cursor-pointer">
                {emoji} {count > 1 && count}
              </button>
            ))}
          </div>
        )}

        {/* Hover triggers */}
        <div className="absolute -top-2 right-0 opacity-0 group-hover:opacity-100 flex gap-0.5 transition-opacity">
          <button onClick={() => setShowEmojiPicker(!showEmojiPicker)} className="p-1 bg-dark-800 rounded-full border border-dark-600" title="Реакция">
            <Smile size={12} className="text-dark-400" />
          </button>
          <button onClick={() => setShowMenu(!showMenu)} className="p-1 bg-dark-800 rounded-full border border-dark-600" title="Действия">
            <MoreHorizontal size={12} className="text-dark-400" />
          </button>
        </div>

        {showEmojiPicker && (
          <div className={`absolute top-6 ${isMine ? 'right-0' : 'left-0'} z-50 bg-dark-800 border border-dark-600 rounded-xl shadow-xl p-2 flex gap-1`}>
            {QUICK_EMOJIS.map((e) => (
              <button key={e} onClick={() => handleReaction(e)} className="w-7 h-7 rounded hover:bg-dark-700 flex items-center justify-center text-sm">
                {e}
              </button>
            ))}
          </div>
        )}

        {showMenu && (
          <div className={`absolute top-6 ${isMine ? 'right-8' : 'left-8'} z-50 bg-dark-800 border border-dark-600 rounded-xl shadow-xl py-1 min-w-[160px]`}>
            <button onClick={() => { onReply(msg); setShowMenu(false) }} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-dark-300 hover:bg-dark-700 hover:text-white">
              <Reply size={12} /> Ответить
            </button>
            <button onClick={() => { setShowForward(true); setShowMenu(false) }} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-dark-300 hover:bg-dark-700 hover:text-white">
              <Forward size={12} /> Переслать
            </button>
            {msg.content && (
              <button onClick={handleCopy} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-dark-300 hover:bg-dark-700 hover:text-white">
                <Copy size={12} /> Копировать
              </button>
            )}
            {isMine && (msg.message_type === 'text' || msg.message_type === 'poll') && (
              <button onClick={() => { onEdit(msg); setShowMenu(false) }} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-dark-300 hover:bg-dark-700 hover:text-white">
                <Pencil size={12} /> Редактировать
              </button>
            )}
            {(isMine || canDeleteOthers) && (
              <button onClick={() => { onDelete(msg); setShowMenu(false) }} className="w-full flex items-center gap-2 px-3 py-1.5 text-xs text-red-400 hover:bg-dark-700">
                <Trash2 size={12} /> Удалить
              </button>
            )}
          </div>
        )}
      </div>

      {showForward && <ForwardMessageModal message={msg} onClose={() => setShowForward(false)} />}
    </div>
  )
}

function FileAttachment({ a, allowDownload }) {
  const inner = (
    <div className="flex items-center gap-2 bg-dark-700/50 rounded-lg p-2.5 hover:bg-dark-700 transition-colors">
      <div className="w-8 h-8 bg-primary-600/20 rounded-lg flex items-center justify-center flex-shrink-0">
        <FileText size={14} className="text-primary-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white truncate">{a.file_name}</p>
        <p className="text-[10px] text-dark-400">{formatFileSize(a.file_size)}</p>
      </div>
      {allowDownload ? <Download size={14} className="text-dark-400" /> : <Lock size={14} className="text-dark-500" />}
    </div>
  )
  if (!allowDownload) {
    return (
      <div className="relative" title="Отправитель запретил скачивание">
        {inner}
      </div>
    )
  }
  return (
    <a href={a.file_url} target="_blank" download={a.file_name}>
      {inner}
    </a>
  )
}

function MessageStatus({ msg }) {
  if (msg.sending) return <Clock size={11} className="text-primary-200/70" />
  if (msg.is_read) return <CheckCheck size={13} className="text-primary-100" />
  return <Check size={13} className="text-primary-200/90" />
}

function groupReactions(reactions) {
  const map = {}
  reactions.forEach((r) => { map[r.emoji] = (map[r.emoji] || 0) + 1 })
  return Object.entries(map)
}

function formatVoiceTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' Б'
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' КБ'
  return (bytes / 1048576).toFixed(1) + ' МБ'
}

function renderContent(text) {
  if (!text) return null
  const urlRegex = /(https?:\/\/[^\s]+)/g
  const parts = text.split(urlRegex)
  return parts.map((part, i) =>
    urlRegex.test(part) ? <a key={i} href={part} target="_blank" rel="noopener" className="text-primary-400 hover:underline break-all">{part}</a> : part
  )
}
