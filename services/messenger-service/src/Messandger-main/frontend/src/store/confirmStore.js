import { create } from 'zustand'

export const useConfirmStore = create((set, get) => ({
  open: false,
  title: '',
  message: '',
  confirmText: 'Удалить',
  cancelText: 'Отмена',
  danger: true,
  resolver: null,

  ask: (opts) => {
    return new Promise((resolve) => {
      set({
        open: true,
        title: opts.title || 'Подтверждение',
        message: opts.message || 'Вы точно хотите продолжить?',
        confirmText: opts.confirmText || 'Удалить',
        cancelText: opts.cancelText || 'Отмена',
        danger: opts.danger !== false,
        resolver: resolve,
      })
    })
  },

  confirm: () => {
    const { resolver } = get()
    resolver && resolver(true)
    set({ open: false, resolver: null })
  },

  cancel: () => {
    const { resolver } = get()
    resolver && resolver(false)
    set({ open: false, resolver: null })
  },
}))

export const confirmDelete = (message, title = 'Подтвердите удаление') =>
  useConfirmStore.getState().ask({ title, message, confirmText: 'Удалить', danger: true })
