import { create } from 'zustand'
import api from '../api/axios'

export const useChatStore = create((set, get) => ({
  chats: [],
  activeChat: null,
  messages: [],
  loadingMessages: false,
  typingUsers: {},

  fetchChats: async () => {
    try {
      const res = await api.get('/chats/')
      set({ chats: res.data })
    } catch (e) {
      console.error(e)
    }
  },

  setActiveChat: async (chat) => {
    set({ activeChat: chat, messages: [], loadingMessages: true })
    // Сразу обнуляем счётчик непрочитанных в локальном списке чатов
    set((s) => ({
      chats: s.chats.map((c) => c.id === chat.id ? { ...c, unread_count: 0 } : c),
    }))
    try {
      const res = await api.get(`/chats/${chat.id}/messages`)
      set({ messages: res.data, loadingMessages: false })
      // Mark the latest message as read on the server (so other side's ticks update)
      const last = res.data[res.data.length - 1]
      if (last) {
        api.post(`/chats/${chat.id}/read`, { message_id: last.id })
          .then(() => get().fetchChats())
          .catch(() => {})
      }
    } catch (e) {
      set({ loadingMessages: false })
    }
  },

  sendMessage: async (chatId, content, replyToId) => {
    // Optimistic insert with sending=true (clock icon)
    const tempId = `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    const optimistic = {
      id: tempId,
      chat_id: chatId,
      content,
      message_type: 'text',
      sender_id: null,
      sending: true,
      is_read: false,
      attachments: [],
      reactions: [],
      reply_to: null,
      created_at: new Date().toISOString(),
    }
    set((s) => ({ messages: [...s.messages, optimistic] }))
    try {
      const res = await api.post(`/chats/${chatId}/messages`, {
        content,
        reply_to_id: replyToId || null,
      })
      // Replace optimistic message with server message
      set((s) => ({ messages: s.messages.map((m) => m.id === tempId ? { ...res.data, sending: false } : m) }))
      get().fetchChats()
      return res.data
    } catch (e) {
      set((s) => ({ messages: s.messages.filter((m) => m.id !== tempId) }))
      return null
    }
  },

  markChatRead: (chatId, readerId) => {
    // Mark all my messages in this chat as read by this reader
    const { activeChat } = get()
    if (activeChat?.id !== chatId) return
    set((s) => ({
      messages: s.messages.map((m) =>
        m.sender_id && m.sender_id !== readerId ? { ...m, is_read: true } : m
      ),
    }))
  },

  editMessage: async (chatId, messageId, content) => {
    try {
      await api.put(`/chats/${chatId}/messages/${messageId}`, { content })
      set((s) => ({
        messages: s.messages.map((m) =>
          m.id === messageId ? { ...m, content, is_edited: true } : m
        ),
      }))
    } catch (e) {}
  },

  deleteMessage: async (chatId, messageId) => {
    try {
      const res = await api.delete(`/chats/${chatId}/messages/${messageId}`)
      const hardDelete = res.data?.hard_delete
      if (hardDelete) {
        set((s) => ({ messages: s.messages.filter((m) => m.id !== messageId) }))
      } else {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === messageId ? { ...m, is_deleted: true, content: null } : m
          ),
        }))
      }
    } catch (e) {}
  },

  handleMessageDeleted: (chatId, messageId, hardDelete) => {
    const { activeChat } = get()
    if (activeChat?.id === chatId) {
      if (hardDelete) {
        set((s) => ({ messages: s.messages.filter((m) => m.id !== messageId) }))
      } else {
        set((s) => ({
          messages: s.messages.map((m) =>
            m.id === messageId ? { ...m, is_deleted: true, content: null } : m
          ),
        }))
      }
    }
  },

  createChat: async (chatType, name, memberIds) => {
    try {
      const res = await api.post('/chats/', { chat_type: chatType, name, member_ids: memberIds })
      await get().fetchChats()
      const chats = get().chats
      return chats.find((c) => c.id === res.data.id)
    } catch (e) {
      return null
    }
  },

  searchUsers: async (q) => {
    try {
      const res = await api.get(`/auth/users?q=${q}`)
      return res.data
    } catch (e) {
      return []
    }
  },

  addTypingUser: (chatId, userId) => {
    set((s) => {
      const current = s.typingUsers[chatId] || []
      if (!current.includes(userId)) {
        return { typingUsers: { ...s.typingUsers, [chatId]: [...current, userId] } }
      }
      return s
    })
  },

  removeTypingUser: (chatId, userId) => {
    set((s) => {
      const current = s.typingUsers[chatId] || []
      return { typingUsers: { ...s.typingUsers, [chatId]: current.filter((u) => u !== userId) } }
    })
  },

  addMessage: (chatId, message) => {
    const { activeChat } = get()
    if (activeChat?.id === chatId) {
      set((s) => ({ messages: [...s.messages, message] }))
    }
    get().fetchChats()
  },
}))
