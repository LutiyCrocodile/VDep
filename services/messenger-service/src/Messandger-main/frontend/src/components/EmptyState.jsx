import { MessageSquare } from 'lucide-react'

export default function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center bg-dark-950">
      <div className="text-center">
        <MessageSquare size={64} className="mx-auto mb-4 text-dark-600" />
        <h3 className="text-xl font-semibold text-dark-400 mb-2">Выберите чат</h3>
        <p className="text-dark-500 text-sm">Выберите чат из списка или начните новую переписку</p>
      </div>
    </div>
  )
}
