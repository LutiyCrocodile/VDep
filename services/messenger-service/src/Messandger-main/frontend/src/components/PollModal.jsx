import { useState } from 'react'
import { X, Plus, Trash2, BarChart3 } from 'lucide-react'
import api from '../api/axios'
import toast from 'react-hot-toast'
import { useChatStore } from '../store/chatStore'
import { useWebSocketStore } from '../store/websocketStore'

export default function PollModal({ chatId, onClose }) {
  const { activeChat } = useChatStore()
  const { sendMessage: wsSendMessage } = useWebSocketStore()
  const memberIds = activeChat?.members?.map((m) => String(m.user_id)) || []
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState(['', ''])
  const [isAnonymous, setIsAnonymous] = useState(false)
  const [isMultiple, setIsMultiple] = useState(false)

  const addOption = () => { if (options.length < 10) setOptions([...options, '']) }
  const removeOption = (i) => { if (options.length > 2) setOptions(options.filter((_, idx) => idx !== i)) }
  const updateOption = (i, val) => { const copy = [...options]; copy[i] = val; setOptions(copy) }

  const handleCreate = async () => {
    if (!question.trim()) { toast.error('Введите вопрос'); return }
    const validOptions = options.filter((o) => o.trim())
    if (validOptions.length < 2) { toast.error('Минимум 2 варианта'); return }

    try {
      const res = await api.post('/polls/', {
        chat_id: chatId,
        question: question.trim(),
        options: validOptions,
        is_anonymous: isAnonymous,
        is_multiple_choice: isMultiple,
      })
      // Append poll message to active chat and broadcast via WebSocket
      useChatStore.setState((s) => ({ messages: [...s.messages, res.data] }))
      wsSendMessage(chatId, res.data, memberIds.filter((id) => id !== String(res.data.sender_id)))
      useChatStore.getState().fetchChats()
      toast.success('Опрос создан')
      onClose()
    } catch (e) {
      toast.error('Ошибка создания опроса')
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-md">
        <div className="flex items-center justify-between p-4 border-b border-dark-700">
          <h3 className="text-lg font-bold text-white flex items-center gap-2"><BarChart3 size={20} className="text-primary-400" /> Создать опрос</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-dark-700 text-dark-400 hover:text-white"><X size={20} /></button>
        </div>

        <div className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-dark-300 mb-1">Вопрос</label>
            <textarea value={question} onChange={(e) => setQuestion(e.target.value)} className="input-field" rows={2} placeholder="Задайте вопрос..." />
          </div>

          <div>
            <label className="block text-xs font-medium text-dark-300 mb-2">Варианты ответа</label>
            <div className="space-y-2">
              {options.map((opt, i) => (
                <div key={i} className="flex gap-2">
                  <input type="text" value={opt} onChange={(e) => updateOption(i, e.target.value)} className="input-field flex-1" placeholder={`Вариант ${i + 1}`} />
                  {options.length > 2 && (
                    <button onClick={() => removeOption(i)} className="p-2 text-red-400 hover:bg-dark-800 rounded-lg"><Trash2 size={16} /></button>
                  )}
                </div>
              ))}
            </div>
            {options.length < 10 && (
              <button onClick={addOption} className="mt-2 flex items-center gap-1 text-primary-400 text-xs hover:text-primary-300">
                <Plus size={14} /> Добавить вариант
              </button>
            )}
          </div>

          <div className="flex gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={isAnonymous} onChange={(e) => setIsAnonymous(e.target.checked)} className="w-4 h-4 rounded accent-primary-600" />
              <span className="text-xs text-dark-300">Анонимный</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={isMultiple} onChange={(e) => setIsMultiple(e.target.checked)} className="w-4 h-4 rounded accent-primary-600" />
              <span className="text-xs text-dark-300">Несколько ответов</span>
            </label>
          </div>

          <button onClick={handleCreate} className="btn-primary w-full">Создать опрос</button>
        </div>
      </div>
    </div>
  )
}
