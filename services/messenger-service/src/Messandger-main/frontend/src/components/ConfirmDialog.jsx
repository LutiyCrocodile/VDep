import { AlertTriangle, X } from 'lucide-react'
import { useConfirmStore } from '../store/confirmStore'

export default function ConfirmDialog() {
  const { open, title, message, confirmText, cancelText, danger, confirm, cancel } = useConfirmStore()

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-[200] flex items-center justify-center p-4" onClick={cancel}>
      <div className="bg-dark-900 rounded-2xl border border-dark-700 shadow-2xl w-full max-w-sm animate-in fade-in zoom-in-95 duration-150" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start gap-4 p-5">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 ${danger ? 'bg-red-500/15 text-red-400' : 'bg-primary-500/15 text-primary-400'}`}>
            <AlertTriangle size={22} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-bold text-base mb-1">{title}</h3>
            <p className="text-dark-300 text-sm">{message}</p>
          </div>
          <button onClick={cancel} className="p-1 text-dark-400 hover:text-white" title="Закрыть"><X size={18} /></button>
        </div>
        <div className="flex gap-2 p-4 pt-0 justify-end">
          <button onClick={cancel} className="px-4 py-2 text-sm text-dark-300 hover:bg-dark-800 rounded-lg transition-colors">{cancelText}</button>
          <button onClick={confirm} className={`px-4 py-2 text-sm rounded-lg text-white font-medium transition-colors shadow-lg ${danger ? 'bg-red-600 hover:bg-red-700 shadow-red-500/20' : 'bg-primary-600 hover:bg-primary-700 shadow-primary-500/20'}`}>{confirmText}</button>
        </div>
      </div>
    </div>
  )
}
