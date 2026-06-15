import { create } from 'zustand'

const STORAGE_KEY = 'gkm-theme'

function applyTheme(theme) {
  const root = document.documentElement
  root.classList.remove('light', 'dark')
  root.classList.add(theme)
  root.setAttribute('data-theme', theme)
}

const initial = (() => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch {}
  return 'dark'
})()

applyTheme(initial)

export const useThemeStore = create((set, get) => ({
  theme: initial,
  toggleTheme: () => {
    const next = get().theme === 'dark' ? 'light' : 'dark'
    applyTheme(next)
    try { localStorage.setItem(STORAGE_KEY, next) } catch {}
    set({ theme: next })
  },
  setTheme: (t) => {
    applyTheme(t)
    try { localStorage.setItem(STORAGE_KEY, t) } catch {}
    set({ theme: t })
  },
}))
