import { useEffect } from 'react'
import { X, Download } from 'lucide-react'
import { useLightboxStore } from '../store/lightboxStore'

export default function Lightbox() {
  const { open, src, name, allowDownload, hide } = useLightboxStore()

  useEffect(() => {
    if (!open) return
    const onKey = (e) => { if (e.key === 'Escape') hide() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, hide])

  if (!open || !src) return null

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4"
      onClick={hide}
    >
      <div className="absolute top-4 right-4 flex items-center gap-2 z-10">
        {allowDownload && (
          <a
            href={src}
            download={name || true}
            onClick={(e) => e.stopPropagation()}
            className="px-3 py-2 bg-dark-800/80 hover:bg-dark-700 text-white rounded-xl flex items-center gap-2 text-sm backdrop-blur"
            title="Скачать"
          >
            <Download size={16} /> Скачать
          </a>
        )}
        <button
          onClick={hide}
          className="p-2 bg-dark-800/80 hover:bg-dark-700 text-white rounded-xl backdrop-blur"
          title="Закрыть (Esc)"
        >
          <X size={18} />
        </button>
      </div>
      <img
        src={src}
        alt={name}
        onClick={(e) => e.stopPropagation()}
        className="max-w-[95vw] max-h-[90vh] rounded-xl shadow-2xl object-contain"
      />
    </div>
  )
}
