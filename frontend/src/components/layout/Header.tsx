'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/services/auth';
import { useRouter } from 'next/navigation';
import { channelsAPI } from '@/services/api';
import { useSidebar } from '@/contexts/SidebarContext';
import { getPortalLoginUrl } from '@/lib/portal-url';

export default function Header() {
  const [searchQuery, setSearchQuery] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const { isCollapsed, toggleSidebar } = useSidebar();

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
      router.push(`/?q=${encodeURIComponent(searchQuery)}`);
    } else {
      router.push('/');
    }
  };

  return (
    <header className="fixed top-0 left-0 right-0 h-14 bg-dgi-surface/95 backdrop-blur-md z-50 flex items-center justify-between px-4 border-b border-dgi-border shadow-sm">
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleSidebar}
          className="p-2 hover:bg-dgi-surface-hover rounded-full transition-all duration-200"
        >
          <svg 
            className={`w-6 h-6 text-dgi-text transition-transform duration-300 ease-in-out ${isCollapsed ? 'rotate-90' : 'rotate-0'}`} 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24" 
            strokeWidth={1.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-8 h-8 bg-gradient-to-br from-dgi-primary to-dgi-primary-mid rounded-lg flex items-center justify-center shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] group-hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)] transition-all duration-300">
            <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
            </svg>
          </div>
          <span className="text-xl font-bold text-dgi-text font-heading hidden sm:block">Видеохостинг ДГИ</span>
        </Link>
      </div>

      <div className="flex-1 max-w-2xl mx-4">
        <form onSubmit={handleSearch} className="flex">
          <div className="flex-1 flex items-center bg-dgi-surface border border-dgi-border rounded-l-full px-4 focus-within:border-dgi-primary/50 focus-within:ring-2 focus-within:ring-dgi-primary/20 transition-all duration-200">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Поиск видео..."
              className="w-full bg-transparent text-dgi-text py-2 outline-none placeholder:text-dgi-muted"
            />
          </div>
          <button
            type="submit"
            className="bg-dgi-surface hover:bg-dgi-surface-hover border border-l-0 border-dgi-border rounded-r-full px-5 py-2 transition-all duration-200 hover:border-dgi-primary/30"
          >
            <svg className="w-5 h-5 text-dgi-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
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
              className="flex items-center gap-2 bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:opacity-90 text-white px-4 py-2 rounded-full transition-all duration-200 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)]"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
              </svg>
              <span className="hidden sm:block text-sm font-medium">Создать</span>
            </Link>
            <button className="p-2 hover:bg-dgi-surface-hover rounded-full transition-all duration-200">
              <svg className="w-6 h-6 text-dgi-text" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </button>
            <Link 
              href={userChannel ? `/channel/${userChannel.handle}` : '/channel'}
              className="w-9 h-9 bg-gradient-to-br from-dgi-primary to-dgi-primary-mid rounded-full flex items-center justify-center text-white font-medium shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)] transition-all"
              title={userChannel ? 'Мой канал' : 'Создать канал'}
            >
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </Link>
          </>
        ) : (
          <a
            href={getPortalLoginUrl()}
            className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:opacity-90 text-white px-5 py-2 rounded-full text-sm font-medium transition-all duration-200 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)]"
          >
            Войти через портал
          </a>
        )}
      </div>
    </header>
  );
}
