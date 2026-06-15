import { create } from 'zustand'

// Глобальная модалка просмотра фото
export const useLightboxStore = create((set) => ({
  open: false,
  src: null,
  name: '',
  allowDownload: true,
  show: (src, name = '', allowDownload = true) => set({ open: true, src, name, allowDownload }),
  hide: () => set({ open: false, src: null, name: '', allowDownload: true }),
}))
