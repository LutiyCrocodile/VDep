import { useEffect, useState } from 'react'
import { X, Image as ImageIcon, FileText, Link2, Music, Video, Download } from 'lucide-react'
import api from '../api/axios'
import { useLightboxStore } from '../store/lightboxStore'

const TABS = [
  { id: 'image', label: 'Фото', icon: ImageIcon },
  { id: 'video', label: 'Видео', icon: Video },
  { id: 'file', label: 'Файлы', icon: FileText },
  { id: 'audio', label: 'Музыка', icon: Music },
  { id: 'link', label: 'Ссылки', icon: Link2 },
]

export default function MediaGalleryModal({ chatId, title = 'Файлы и медиа', onClose }) {
  const [tab, setTab] = useState('image')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const show = useLightboxStore((s) => s.show)

  useEffect(() => {
    let active = true
    setLoading(true)
    api
      .get(`/chats/${chatId}/media`, { params: { kind: tab } })
      .then((r) => { if (active) setItems(r.data) })
      .catch(() => { if (active) setItems([]) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [chatId, tab])

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4" onClick={onClose}>
      <div className="bg-dark-900 rounded-2xl border border-dark-700 w-full max-w-3xl max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="p-4 border-b border-dark-700 flex items-center justify-between">
          <h3 className="font-heading font-bold text-white">{title}</h3>
          <button onClick={onClose} className="p-1 text-dark-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="flex gap-1 px-3 py-2 border-b border-dark-700 overflow-x-auto">
          {TABS.map((t) => {
            const Icon = t.icon
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 flex-shrink-0 ${tab === t.id ? 'bg-primary-600 text-white' : 'text-dark-400 hover:bg-dark-800'}`}
              >
                <Icon size={13} /> {t.label}
              </button>
            )
          })}
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <p className="text-center text-dark-400 text-sm py-8">Загрузка...</p>
          ) : items.length === 0 ? (
            <p className="text-center text-dark-400 text-sm py-8">Ничего не найдено</p>
          ) : tab === 'image' ? (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {items.map((it) => (
                <button
                  key={it.attachment_id}
                  onClick={() => show(it.file_url, it.file_name, it.allow_download)}
                  className="aspect-square rounded-lg overflow-hidden hover:opacity-80 transition-opacity"
                >
                  <img src={it.file_url} alt={it.file_name} className="w-full h-full object-cover" />
                </button>
              ))}
            </div>
          ) : tab === 'video' ? (
            <div className="grid grid-cols-2 gap-2">
              {items.map((it) => (
                <video key={it.attachment_id} src={it.file_url} controls className="rounded-lg w-full" />
              ))}
            </div>
          ) : tab === 'link' ? (
            <div className="space-y-2">
              {items.map((it, i) => (
                <a key={`${it.message_id}-${i}`} href={it.url} target="_blank" rel="noopener" className="block bg-dark-800 hover:bg-dark-700 rounded-xl p-3 text-sm text-primary-400 break-all">
                  {it.url}
                </a>
              ))}
            </div>
          ) : (
            <div className="space-y-2">
              {items.map((it) => (
                <div key={it.attachment_id} className="flex items-center gap-3 bg-dark-800 rounded-xl p-3">
                  {tab === 'audio' ? <Music size={18} className="text-primary-400" /> : <FileText size={18} className="text-primary-400" />}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white truncate">{it.file_name}</p>
                    <p className="text-[10px] text-dark-400">{formatBytes(it.file_size)} · {new Date(it.created_at).toLocaleDateString('ru')}</p>
                    {tab === 'audio' && it.allow_download && <audio src={it.file_url} controls className="w-full max-w-xs mt-1.5" />}
                  </div>
                  {it.allow_download ? (
                    <a href={it.file_url} download={it.file_name} className="p-2 text-dark-400 hover:text-white" title="Скачать">
                      <Download size={16} />
                    </a>
                  ) : (
                    <span className="text-[10px] text-dark-500 italic px-2">Скачивание запрещено</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function formatBytes(b) {
  if (!b) return ''
  if (b < 1024) return b + ' Б'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' КБ'
  return (b / 1048576).toFixed(1) + ' МБ'
}
