import { create } from 'zustand'
import toast from 'react-hot-toast'
import { useChatStore } from './chatStore'
import { useCallStore } from './callStore'
import { usePresenceStore } from './presenceStore'

export const useWebSocketStore = create((set, get) => ({
  ws: null,
  connected: false,

  connect: (token, userId) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws?token=${token}`)
    const currentUserId = userId || null

    ws.onopen = () => set({ ws, connected: true })
    ws.onclose = () => {
      set({ connected: false })
      setTimeout(() => get().connect(token, userId), 3000)
    }
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      const chatStore = useChatStore.getState()

      if (data.type === 'new_message') {
        // Не добавляем если это наше собственное сообщение (оно уже добавлено через API),
        // но для отложенных (worker disptached) — добавляем всегда.
        if (data.message?.sender_id !== currentUserId) {
          chatStore.addMessage(data.chat_id, data.message)
        } else if (data.is_scheduled_dispatch) {
          chatStore.addMessage(data.chat_id, data.message)
        }
      } else if (data.type === 'typing') {
        // Не показываем "печатает" самому себе
        if (data.user_id !== currentUserId) {
          chatStore.addTypingUser(data.chat_id, data.user_id)
        }
      } else if (data.type === 'stop_typing') {
        if (data.user_id !== currentUserId) {
          chatStore.removeTypingUser(data.chat_id, data.user_id)
        }
      } else if (data.type === 'read') {
        chatStore.markChatRead?.(data.chat_id, data.user_id)
      } else if (data.type === 'presence') {
        usePresenceStore.getState().setPresence(data.user_id, data.status, data.last_seen)
      } else if (data.type === 'message_deleted') {
        chatStore.handleMessageDeleted(data.chat_id, data.message_id, data.hard_delete)
      } else if (data.type === 'notification') {
        const icon = data.notif_type === 'warning' ? '⚠️' : data.notif_type === 'announcement' ? '📢' : 'ℹ️'
        toast(`${icon} ${data.title}${data.body ? '\n' + data.body : ''}`, { duration: 6000 })
      } else if (data.type === 'call_invite') {
        useCallStore.getState().setIncomingCall(data)
      } else if (data.type === 'broadcast_started') {
        console.log('Broadcast started:', data)
        // Показать уведомление о начале трансляции
        toast(`📡 Трансляция начана: ${data.from_name}`, { duration: 5000 })
        // Можно добавить кнопку для присоединения к трансляции
        useCallStore.getState().setBroadcastInfo(data)
        // Добавить системное сообщение в чат
        const chatStore = useChatStore.getState()
        chatStore.addMessage(data.chat_id, {
          id: `broadcast_${data.call_id}`,
          sender_id: 'system',
          sender_first_name: 'Система',
          sender_last_name: '',
          content: data.call_type === 'video' ? '📡 Началась видеотрансляция' : '📡 Началась аудиотрансляция',
          created_at: new Date().toISOString(),
          is_system: true,
        })
      } else if (data.type === 'broadcast_join_request') {
        console.log('Broadcast join request:', data)
        // Ведущий получает запрос от зрителя и должен отправить offer
        window.__callHandlers?.handleBroadcastJoinRequest(data)
      } else if (data.type === 'call_accept') {
        window.__callHandlers?.handleCallAccepted(data)
      } else if (data.type === 'call_reject') {
        window.__callHandlers?.handleCallRejected(data)
      } else if (data.type === 'call_leave') {
        console.log('Call leave:', data)
        // Участник покинул звонок - удаляем его из списка участников
        window.__callHandlers?.handleCallLeave(data)
      } else if (data.type === 'call_end') {
        window.__callHandlers?.handleCallEnded(data)
      } else if (data.type === 'call_signal') {
        window.__callHandlers?.handleSignal(data)
      }
    }

    set({ ws })
  },

  sendMessage: (chatId, message, recipients) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'message', chat_id: chatId, message, recipients }))
    }
  },

  sendTyping: (chatId, recipients) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'typing', chat_id: chatId, recipients }))
    }
  },

  sendStopTyping: (chatId, recipients) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop_typing', chat_id: chatId, recipients }))
    }
  },

  sendRead: (chatId, recipients) => {
    const { ws } = get()
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'read', chat_id: chatId, recipients }))
    }
  },
}))
