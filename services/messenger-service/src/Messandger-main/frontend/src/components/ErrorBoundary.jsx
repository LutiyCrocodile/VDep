import React from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    // Лог в консоль — на проде заменить на отправку в backend
    console.error('[ErrorBoundary]', error, info)
  }

  reset = () => this.setState({ hasError: false, error: null })

  render() {
    if (!this.state.hasError) return this.props.children
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-950 p-6">
        <div className="bg-dark-900 border border-red-900/50 rounded-2xl p-8 max-w-md text-center shadow-2xl">
          <div className="w-14 h-14 rounded-full bg-red-600/15 mx-auto mb-4 flex items-center justify-center">
            <AlertTriangle size={28} className="text-red-400" />
          </div>
          <h3 className="text-white font-bold text-lg mb-2">Что-то пошло не так</h3>
          <p className="text-dark-400 text-sm mb-4">
            Произошла непредвиденная ошибка в приложении. Перезагрузите страницу. Если ошибка повторяется — обратитесь в Управление информатизации.
          </p>
          {this.state.error && (
            <pre className="text-left text-[11px] text-red-300/80 bg-dark-950/80 rounded-lg p-3 mb-4 overflow-auto max-h-32">
              {String(this.state.error?.message || this.state.error)}
            </pre>
          )}
          <div className="flex gap-2 justify-center">
            <button onClick={() => window.location.reload()} className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm rounded-lg flex items-center gap-2 transition-colors">
              <RefreshCw size={14} /> Перезагрузить
            </button>
            <button onClick={this.reset} className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-dark-200 text-sm rounded-lg transition-colors">
              Закрыть
            </button>
          </div>
        </div>
      </div>
    )
  }
}
