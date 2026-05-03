// Единая цветовая палитра приложения (сине-фиолетовая тема)
export const theme = {
  // Фон
  bg: {
    primary: '#0a0a1a',      // Основной фон
    secondary: '#121228',    // Вторичный фон
    tertiary: '#1a1a3e',     // Третичный фон (карточки)
    hover: '#252550',        // Hover состояние
  },
  // Акцентные цвета
  accent: {
    primary: '#6366f1',      // Основной акцент (indigo)
    secondary: '#8b5cf6',    // Вторичный акцент (violet)
    gradient: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
  },
  // Текст
  text: {
    primary: '#ffffff',
    secondary: '#a1a1aa',
    muted: '#71717a',
  },
  // Границы
  border: {
    primary: '#27274a',
    secondary: '#3f3f6f',
  },
  // Кнопки
  button: {
    primary: 'bg-indigo-600 hover:bg-indigo-500',
    secondary: 'bg-violet-600 hover:bg-violet-500',
    ghost: 'bg-[#1a1a3e] hover:bg-[#252550]',
  },
  // Статусы
  status: {
    success: '#22c55e',
    error: '#ef4444',
    warning: '#f59e0b',
  }
};

// Tailwind классы для быстрого использования
export const tw = {
  // Фон страницы
  pageBg: 'bg-[#0a0a1a]',
  // Карточки
  card: 'bg-[#1a1a3e] rounded-xl border border-[#27274a]',
  // Кнопки
  btnPrimary: 'bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg transition-all',
  btnSecondary: 'bg-violet-600 hover:bg-violet-500 text-white px-4 py-2 rounded-lg transition-all',
  btnGhost: 'bg-[#1a1a3e] hover:bg-[#252550] text-white px-4 py-2 rounded-lg transition-all border border-[#27274a]',
  // Текст
  textPrimary: 'text-white',
  textSecondary: 'text-zinc-400',
  // Заголовки
  heading: 'text-white font-bold',
  // Input
  input: 'bg-[#121228] border border-[#27274a] rounded-lg px-4 py-2 text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none transition-colors',
  // Hover
  hover: 'hover:bg-[#252550] transition-colors',
};
