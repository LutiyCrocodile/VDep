import type { Metadata } from 'next'
import './globals.css'
import { AuthProvider } from '@/services/auth'
import { SidebarProvider } from '@/contexts/SidebarContext'

export const metadata: Metadata = {
  title: 'Видеохостинг ДГИ',
  description: 'Система видеохостинга для Департамента городского имущества Москвы',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body className="font-sans">
        <AuthProvider>
          <SidebarProvider>
            {children}
          </SidebarProvider>
        </AuthProvider>
      </body>
    </html>
  )
}
