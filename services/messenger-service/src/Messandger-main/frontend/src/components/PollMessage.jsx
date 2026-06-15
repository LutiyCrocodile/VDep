import { useState } from 'react'
import { BarChart3, Check, Lock } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'

export default function PollMessage({ poll, isMine }) {
  const [localPoll, setLocalPoll] = useState(poll)
  const [voting, setVoting] = useState(false)
  const [selected, setSelected] = useState([])

  const totalVotes = localPoll.total_votes || 0
  const hasVoted = localPoll.options.some((o) => o.voted_by_me)
  const isClosed = localPoll.closes_at && new Date(localPoll.closes_at) < new Date()
  const showResults = hasVoted || isClosed
  const barBg = isMine ? 'bg-white/15' : 'bg-dark-700/60'
  const barFill = isMine ? 'bg-white/30' : 'bg-primary-500/40'

  const toggleOption = (optId) => {
    if (showResults) return
    if (localPoll.is_multiple_choice) setSelected((p) => p.includes(optId) ? p.filter((x) => x !== optId) : [...p, optId])
    else setSelected([optId])
  }

  const submitVote = async () => {
    if (!selected.length) { toast.error('Выберите вариант'); return }
    setVoting(true)
    try {
      await api.post(`/polls/${localPoll.id}/vote`, { option_ids: selected })
      const res = await api.get(`/polls/${localPoll.id}`)
      setLocalPoll(res.data)
      setSelected([])
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Ошибка')
    } finally { setVoting(false) }
  }

  return (
    <div className="min-w-[240px] max-w-[340px] space-y-2">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider opacity-70">
        <BarChart3 size={11} />
        <span>{localPoll.is_anonymous ? 'Анонимный опрос' : 'Опрос'}</span>
        {localPoll.is_multiple_choice && <span>· Несколько</span>}
        {isClosed && <span className="flex items-center gap-1"><Lock size={10} /> Завершён</span>}
      </div>
      <p className="text-sm font-medium leading-snug">{localPoll.question}</p>
      <div className="space-y-1.5">
        {localPoll.options.map((opt) => {
          const pct = totalVotes > 0 ? Math.round((opt.vote_count / totalVotes) * 100) : 0
          const isSelected = selected.includes(opt.id)
          return (
            <button key={opt.id} onClick={() => toggleOption(opt.id)} disabled={showResults || voting}
              className={`w-full text-left relative rounded-lg overflow-hidden border transition-all ${showResults ? 'cursor-default' : 'cursor-pointer hover:border-primary-400'} ${isSelected ? 'border-primary-400' : 'border-transparent'} ${barBg}`}>
              {showResults && <div className={`absolute inset-0 ${barFill}`} style={{ width: `${pct}%` }} />}
              <div className="relative flex items-center gap-2 px-3 py-2">
                {!showResults && (
                  <div className={`w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0 ${isSelected ? 'border-primary-300 bg-primary-500' : 'border-dark-400'}`}>
                    {isSelected && <Check size={10} className="text-white" />}
                  </div>
                )}
                {showResults && opt.voted_by_me && <Check size={12} className="text-primary-300 flex-shrink-0" />}
                <span className="flex-1 text-xs">{opt.text}</span>
                {showResults && <span className="text-[10px] font-medium opacity-80">{pct}%</span>}
              </div>
            </button>
          )
        })}
      </div>
      {!showResults && (
        <button onClick={submitVote} disabled={voting || !selected.length}
          className="w-full py-1.5 rounded-lg bg-primary-600 hover:bg-primary-700 disabled:opacity-40 text-white text-xs font-medium transition-colors">
          {voting ? 'Отправка...' : 'Проголосовать'}
        </button>
      )}
      <div className="text-[10px] opacity-60 flex items-center justify-between">
        <span>Голосов: {totalVotes}</span>
        {isClosed && <span>Опрос завершён</span>}
      </div>
    </div>
  )
}
