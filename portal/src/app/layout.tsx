import React from 'react'
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Портал ДГИ',
  description: 'Единый портал Департамента городского имущества Москвы',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ru">
      <body className="dgi-theme-light font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
