'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function Home() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <nav className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-indigo-600">Видеохостинг ДГИ</h1>
            </div>
            <div className="flex items-center space-x-4">
              {isLoggedIn ? (
                <>
                  <Link href="/dashboard" className="text-gray-700 hover:text-indigo-600">
                    Панель управления
                  </Link>
                  <button className="text-gray-700 hover:text-indigo-600">
                    Выйти
                  </button>
                </>
              ) : (
                <>
                  <Link href="/login" className="text-gray-700 hover:text-indigo-600">
                    Войти
                  </Link>
                  <Link 
                    href="/register" 
                    className="bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700"
                  >
                    Регистрация
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center">
          <h2 className="text-4xl font-extrabold text-gray-900 sm:text-5xl sm:tracking-tight lg:text-6xl">
            Система видеохостинга
          </h2>
          <p className="mt-4 text-xl text-gray-500">
            Департамент городского имущества Москвы
          </p>
          <div className="mt-8 flex justify-center gap-4">
            <Link 
              href="/videos" 
              className="bg-indigo-600 text-white px-8 py-3 rounded-lg text-lg font-medium hover:bg-indigo-700"
            >
              Смотреть видео
            </Link>
            <Link 
              href="/streams" 
              className="bg-white text-indigo-600 px-8 py-3 rounded-lg text-lg font-medium border-2 border-indigo-600 hover:bg-indigo-50"
            >
              Трансляции
            </Link>
          </div>
        </div>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-indigo-600 mb-4">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Загрузка видео</h3>
            <p className="text-gray-600">
              Загружайте и делитесь видеоматериалами с коллегами
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-indigo-600 mb-4">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Прямые трансляции</h3>
            <p className="text-gray-600">
              Проводите онлайн-трансляции совещаний и мероприятий
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg shadow-md">
            <div className="text-indigo-600 mb-4">
              <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold mb-2">Поиск по контенту</h3>
            <p className="text-gray-600">
              Быстрый поиск по названию, описанию и субтитрам
            </p>
          </div>
        </div>
      </main>
    </div>
  )
}
