'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/services/auth';
import { useRouter } from 'next/navigation';
import { channelsAPI } from '@/services/api';

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    const fetchChannel = async () => {
      if (isAuthenticated) {
        try {
          const channel = await channelsAPI.getUserChannel();
          setUserChannel(channel);
        } catch {
          setUserChannel(null);
        }
      }
    };
    fetchChannel();
  }, [isAuthenticated]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/search?q=${encodeURIComponent(searchQuery)}`);
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-[#0a0a1a]/95 backdrop-blur-md z-50 flex items-center justify-between px-4 border-b border-[#27274a]">
      <div className="flex items-center gap-4">
        <button className="p-2 hover:bg-[#252550] rounded-full transition-all duration-200">
          <svg className="w-6 h-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/40 transition-all duration-300">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
            </svg>
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent hidden sm:block">VideoHost</span>
        </Link>
      </div>

      <div className="flex-1 max-w-2xl mx-4">
        <form onSubmit={handleSearch} className="flex">
          <div className="flex-1 flex items-center bg-[#121228] border border-[#27274a] rounded-l-full px-4 focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/20 transition-all duration-200">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск видео..."
              className="w-full bg-transparent text-white py-2 outline-none placeholder-zinc-500"
            />
          </div>
          <button
            type="submit"
            className="bg-[#1a1a3e] hover:bg-[#252550] border border-l-0 border-[#27274a] rounded-r-full px-5 py-2 transition-all duration-200 hover:border-indigo-500/30"
          >
            <svg className="w-5 h-5 text-zinc-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </button>
        </form>
      </div>

      <div className="flex items-center gap-3">
        {isAuthenticated ? (
          <>
            <Link
              href="/upload"
              className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-4 py-2 rounded-full transition-all duration-200 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:block text-sm font-medium">Создать</span>
            </Link>
            <button className="p-2 hover:bg-[#252550] rounded-full transition-all duration-200">
              <svg className="w-6 h-6 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <Link 
              href={userChannel ? `/channel/${userChannel.handle}` : '/channel'}
              className="w-9 h-9 bg-gradient-to-br from-violet-500 to-fuchsia-600 rounded-full flex items-center justify-center text-white font-medium shadow-lg shadow-violet-500/20 hover:shadow-violet-500/40 transition-all"
              title={userChannel ? 'Мой канал' : 'Создать канал'}
            >
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </Link>
          </>
        ) : (
          <>
            <Link
              href="/login"
              className="text-indigo-400 hover:text-indigo-300 text-sm font-medium mr-2 transition-colors"
            >
              Войти
            </Link>
            <Link
              href="/register"
              className="bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-5 py-2 rounded-full text-sm font-medium transition-all duration-200 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40"
            >
              Регистрация
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
