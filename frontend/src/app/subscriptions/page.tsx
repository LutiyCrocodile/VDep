'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';
import Link from 'next/link';

interface Channel {
  id: string;
  name: string;
  description?: string;
  handle: string;
  avatar_url?: string;
  banner_url?: string;
  owner_id: string;
  subscribers_count: number;
  is_verified: boolean;
  created_at: string;
}

export default function SubscriptionsPage() {
  const { user } = useAuth();
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { isCollapsed } = useSidebar();

  useEffect(() => {
    const fetchSubscriptions = async () => {
      if (user) {
        try {
          const data = await channelsAPI.getSubscriptions();
          console.log('Subscriptions data:', data);
          setChannels(Array.isArray(data) ? data : []);
        } catch (err: any) {
          console.error('Subscriptions error:', err);
          const errorDetail = err.response?.data?.detail || err.message || 'Ошибка загрузки подписок';
          const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
          setError(`Ошибка: ${errorMessage}`);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchSubscriptions();
  }, [user]);

  if (!user) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <main className={`pt-14 min-h-screen flex items-center justify-center transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <div className="text-center">
            <p className="text-white text-xl mb-4">Войдите для просмотра подписок</p>
            <Link
              href="/login"
              className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-3 rounded-lg font-medium transition-all"
            >
              Войти
            </Link>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen dgi-gradient-bg">
      <Header />
      <Sidebar />
      
      <main className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="max-w-7xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-white mb-6">Мои подписки</h1>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          ) : channels.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">У вас пока нет подписок</p>
              <Link
                href="/"
                className="inline-block mt-4 bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-2 rounded-lg font-medium transition-all"
              >
                Найти каналы
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {channels.map((channel) => (
                <Link
                  key={channel.id}
                  href={`/channel/${channel.handle}`}
                  className="bg-dgi-surface/80 backdrop-blur-sm rounded-2xl p-6 border border-dgi-primary/30 hover:border-dgi-primary/50 transition-all duration-300"
                >
                  <div className="flex items-center gap-4 mb-4">
                    <div className="w-16 h-16 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-2xl flex-shrink-0 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)]">
                      {channel.name[0]?.toUpperCase() || 'C'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="text-white font-semibold text-lg truncate">
                        {channel.name}
                      </h3>
                      <p className="text-gray-400 text-sm">@{channel.handle}</p>
                    </div>
                  </div>
                  {channel.description && (
                    <p className="text-gray-300 text-sm line-clamp-2 mb-4">
                      {channel.description}
                    </p>
                  )}
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">
                      {channel.subscribers_count.toLocaleString()} подписчиков
                    </span>
                    {channel.is_verified && (
                      <span className="text-dgi-primary">✓ Проверенный</span>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
