export {}

declare global {
  interface Window {
    ENV?: {
      NEXT_PUBLIC_VIDEO_URL?: string
      NEXT_PUBLIC_AUTH_URL?: string
      NEXT_PUBLIC_MESSENGER_URL?: string
      NEXT_PUBLIC_DASHBOARD_URL?: string
      NEXT_PUBLIC_SUPPORT_URL?: string
    }
  }
}
