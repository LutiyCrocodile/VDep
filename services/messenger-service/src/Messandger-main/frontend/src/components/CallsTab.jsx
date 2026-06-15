import { useEffect, useState } from 'react'
import { Phone, Video, PhoneIncoming, PhoneMissed, PhoneOutgoing, Clock, Plus, Search, X, Calendar, Users } from 'lucide-react'
import api from '../api/axios'
import { useAuthStore } from '../store/authStore'
import toast from 'react-hot-toast'
import Avatar from './Avatar'

export default function CallsTab() {
  const { user } = useAuthStore()
  const [calls, setCalls] = useState([])
  const [showNewCall, setShowNewCall] = useState(false)
  const [callType, setCallType] = useState('audio')
  const [searchQ, setSearchQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [selectedUsers, setSelectedUsers] = useState([])
  const [isSchedule, setIsSchedule] = useState(false)
  const [scheduleDate, setScheduleDate] = useState('')
  const [filter, setFilter] = useState('all') // all, scheduled, missed

  const loadCalls = () => {
    api.get('/calls/').then((r) => setCalls(r.data)).catch(() => {})
  }

  useEffect(() => { loadCalls() }, [])

  const searchUsers = async (q) => {
    setSearchQ(q)
    if (q.length < 2) { setSearchResults([]); return }
    try {
      const r = await api.get(`/auth/users?q=${q}`)
      setSearchResults(r.data.filter(u => !selectedUsers.find(s => s.id === u.id)))
    } catch (e) { setSearchResults([]) }
  }

  const startCall = async () => {
    if (selectedUsers.length === 0) return toast.error('Выберите участников')
    try {
      if (isSchedule) {
        if (!scheduleDate) return toast.error('Укажите дату и время')
        await api.post('/calls/schedule', {
          call_type: callType,
          participant_ids: selectedUsers.map(u => u.id),
          // Конвертируем локальное datetime-local в UTC ISO
          scheduled_at: new Date(scheduleDate).toISOString(),
        })
        toast.success('Звонок запланирован')
      } else {
        const res = await api.post('/calls/', {
          call_type: callType,
          participant_ids: selectedUsers.map(u => u.id),
        })
        // Start WebRTC call
        if (window.__startCall) {
          window.__startCall(callType, selectedUsers.map(u => u.id), res.data.id)
        }
      }
      setShowNewCall(false)
      setSelectedUsers([])
      setSearchQ('')
      setScheduleDate('')
      loadCalls()
    } catch (e) {
      toast.error('Ошибка')
    }
  }

  const filtered = calls.filter(c => {
    if (filter === 'scheduled') return c.status === 'scheduled'
    if (filter === 'missed') return c.status === 'missed'
    return true
  })

  return (
    <div className="flex-1 bg-dark-950 flex flex-col">
      <div className="h-16 px-6 flex items-center justify-between border-b border-dark-700 bg-dark-900">
        <h2 className="text-lg font-bold text-white flex items-center gap-2"><Phone size={20} className="text-primary-400" /> Звонки</h2>
        <button onClick={() => setShowNewCall(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-primary-600 hover:bg-primary-700 text-white text-xs rounded-lg">
          <Plus size={14} /> Новый звонок
        </button>
      </div>

      {/* Filters */}
      <div className="px-4 py-2 border-b border-dark-800 flex gap-2">
        {[
          { key: 'all', label: 'Все' },
          { key: 'scheduled', label: 'Запланированные' },
          { key: 'missed', label: 'Пропущенные' },
        ].map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} className={`px-3 py-1 rounded-lg text-xs ${filter === f.key ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}>{f.label}</button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-dark-400">
            <Phone size={48} className="mb-3 opacity-50" />
            <p className="text-lg font-medium">Нет звонков</p>
            <p className="text-sm">История звонков будет отображаться здесь</p>
          </div>
        ) : (
          <div className="space-y-2 max-w-2xl mx-auto">
            {filtered.map((call) => (
              <CallItem key={call.id} call={call} currentUserId={user?.id} />
            ))}
          </div>
        )}
      </div>

      {/* New Call Modal */}
      {showNewCall && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-dark-900 border border-dark-700 rounded-2xl w-full max-w-md p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-white font-bold">Новый звонок</h3>
              <button onClick={() => { setShowNewCall(false); setSelectedUsers([]) }} className="text-dark-400 hover:text-white"><X size={18} /></button>
            </div>

            {/* Call type */}
            <div className="flex gap-2 mb-4">
              <button onClick={() => setCallType('audio')} className={`flex-1 py-2 rounded-xl text-sm flex items-center justify-center gap-2 ${callType === 'audio' ? 'bg-primary-600 text-white' : 'bg-dark-800 text-dark-400'}`}>
                <Phone size={16} /> Аудиозвонок
              </button>
              <button onClick={() => setCallType('video')} className={`flex-1 py-2 rounded-xl text-sm flex items-center justify-center gap-2 ${callType === 'video' ? 'bg-primary-600 text-white' : 'bg-dark-800 text-dark-400'}`}>
                <Video size={16} /> Видеозвонок
              </button>
            </div>

            {/* Search users */}
            <div className="relative mb-3">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-400" />
              <input type="text" value={searchQ} onChange={(e) => searchUsers(e.target.value)} className="w-full pl-9 pr-4 py-2 bg-dark-800 border border-dark-600 rounded-xl text-sm text-white placeholder-dark-400 focus:outline-none focus:ring-1 focus:ring-primary-500" placeholder="Поиск участников..." />
            </div>

            {searchResults.length > 0 && (
              <div className="bg-dark-800 rounded-xl max-h-32 overflow-y-auto mb-3">
                {searchResults.map(u => (
                  <button key={u.id} onClick={() => { setSelectedUsers(prev => [...prev, u]); setSearchResults(prev => prev.filter(x => x.id !== u.id)); setSearchQ('') }} className="w-full flex items-center gap-2 px-3 py-2 hover:bg-dark-700 text-left">
                    <Avatar name={u.first_name} url={u.avatar_url} size="sm" />
                    <span className="text-sm text-white">{u.first_name} {u.last_name}</span>
                  </button>
                ))}
              </div>
            )}

            {/* Selected */}
            {selectedUsers.length > 0 && (
              <div className="flex gap-1 flex-wrap mb-3">
                {selectedUsers.map(u => (
                  <span key={u.id} className="flex items-center gap-1 bg-dark-800 px-2 py-1 rounded-lg text-xs text-white">
                    {u.first_name} {u.last_name}
                    <button onClick={() => setSelectedUsers(prev => prev.filter(x => x.id !== u.id))} className="text-dark-400 hover:text-red-400"><X size={10} /></button>
                  </span>
                ))}
              </div>
            )}

            {/* Schedule toggle */}
            <label className="flex items-center gap-2 mb-3 cursor-pointer">
              <input type="checkbox" checked={isSchedule} onChange={(e) => setIsSchedule(e.target.checked)} className="rounded bg-dark-800 border-dark-600 text-primary-600 focus:ring-primary-500" />
              <span className="text-sm text-dark-300 flex items-center gap-1"><Calendar size={14} /> Запланировать</span>
            </label>

            {isSchedule && (
              <input type="datetime-local" value={scheduleDate} onChange={(e) => setScheduleDate(e.target.value)} className="w-full bg-dark-800 border border-dark-600 rounded-xl px-3 py-2 text-sm text-white mb-3 focus:outline-none focus:ring-1 focus:ring-primary-500" />
            )}

            <button onClick={startCall} disabled={selectedUsers.length === 0} className="w-full py-2.5 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-xl disabled:opacity-40 flex items-center justify-center gap-2">
              {isSchedule ? <><Calendar size={16} /> Запланировать звонок</> : <><Phone size={16} /> {callType === 'video' ? 'Начать видеозвонок' : 'Начать аудиозвонок'}</>}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function CallItem({ call, currentUserId }) {
  const isInitiator = call.initiator_id === currentUserId
  const icon = call.status === 'missed' ? <PhoneMissed size={16} className="text-red-400" /> :
               call.status === 'ended' ? (isInitiator ? <PhoneOutgoing size={16} className="text-green-400" /> : <PhoneIncoming size={16} className="text-green-400" />) :
               call.status === 'scheduled' ? <Clock size={16} className="text-orange-400" /> :
               call.status === 'active' ? <Phone size={16} className="text-green-400 animate-pulse" /> :
               <PhoneIncoming size={16} className="text-primary-400" />

  const typeIcon = call.call_type === 'video' ? <Video size={14} /> : <Phone size={14} />
  const createdDate = call.created_at ? new Date(call.created_at) : null
  const time = createdDate ? new Date(createdDate.getTime() + 3 * 60 * 60 * 1000).toLocaleString('ru', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''
  const duration = call.duration ? `${Math.floor(call.duration / 60)}:${(call.duration % 60).toString().padStart(2, '0')}` : ''

  const statusLabels = { ringing: 'Звонит...', active: 'Активный', ended: 'Завершён', missed: 'Пропущен', scheduled: 'Запланирован' }

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-dark-900 border border-dark-700 rounded-xl hover:border-dark-600 transition-colors">
      <div className="w-10 h-10 rounded-full bg-dark-800 flex items-center justify-center flex-shrink-0">
        {icon}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-white text-sm font-medium flex items-center gap-1">{typeIcon} {call.call_type === 'video' ? 'Видеозвонок' : 'Аудиозвонок'}</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
            call.status === 'active' ? 'bg-green-500/20 text-green-400' :
            call.status === 'missed' ? 'bg-red-500/20 text-red-400' :
            call.status === 'scheduled' ? 'bg-orange-500/20 text-orange-400' :
            'bg-dark-700 text-dark-400'
          }`}>{statusLabels[call.status] || call.status}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <Users size={10} className="text-dark-500" />
          <span className="text-xs text-dark-400">{call.participants?.length || 0} участников</span>
          <span className="text-xs text-dark-500">{time}</span>
          {duration && <span className="text-xs text-dark-500">({duration})</span>}
        </div>
        {call.status === 'scheduled' && call.scheduled_at && (
          <p className="text-xs text-orange-400 mt-0.5 flex items-center gap-1"><Clock size={10} /> {new Date(new Date(call.scheduled_at).getTime() + 3 * 60 * 60 * 1000).toLocaleString('ru', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}</p>
        )}
      </div>
      {call.status === 'active' && (
        <button onClick={() => api.post(`/calls/${call.id}/join`).then(() => toast.success('Вы присоединились'))} className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-xs rounded-lg" title="Присоединиться к звонку">
          Присоединиться
        </button>
      )}
    </div>
  )
}
