import { create } from 'zustand'

// Карта user_id → { status: 'online'|'offline', last_seen: ISO|null }
export const usePresenceStore = create((set) => ({
  presence: {},
  setPresence: (userId, status, lastSeen = null) => set((s) => ({
    presence: { ...s.presence, [String(userId)]: { status, last_seen: lastSeen } },
  })),
  bulkSet: (map) => set((s) => ({ presence: { ...s.presence, ...map } })),
}))

export function formatLastSeen(iso) {
  if (!iso) return 'был(а) недавно'
  const d = new Date(iso)
  const diff = Date.now() - d.getTime()
  if (diff < 60_000) return 'был(а) только что'
  if (diff < 3600_000) return `был(а) ${Math.floor(diff / 60_000)} мин назад`
  if (diff < 86_400_000) return `был(а) сегодня в ${d.toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}`
  if (diff < 7 * 86_400_000) return `был(а) ${d.toLocaleDateString('ru', { weekday: 'long' })}`
  return `был(а) ${d.toLocaleDateString('ru', { day: '2-digit', month: '2-digit', year: 'numeric' })}`
}
