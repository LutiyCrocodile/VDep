'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import Link from 'next/link';
import { streamsAPI } from '@/services/api';

interface Stream {
  id: string;
  title: string;
  is_live: boolean;
  hls_url?: string;
  rtmp_key?: string;
  created_at: string;
  owner_username?: string;
  viewers_count?: number;
}

export default function StreamsPage() {
  const [streams, setStreams] = useState<Stream[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchStreams = async () => {
      try {
        const data = await streamsAPI.getLiveStreams();
        setStreams(data.streams || []);
      } catch {
        // Mock data
        setStreams([
          {
            id: '1',
            title: 'Прямая трансляция: Совещание ДГИ',
            is_live: true,
            created_at: new Date().toISOString(),
            owner_username: 'Администратор',
            viewers_count: 45,
          },
          {
            id: '2',
            title: 'Обучение новых сотрудников',
            is_live: true,
            created_at: new Date(Date.now() - 3600000).toISOString(),
            owner_username: 'HR отдел',
            viewers_count: 12,
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchStreams();
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU');
  };

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Header />
      <Sidebar />
      
      <main className="ml-64 pt-14 min-h-screen bg-[#0f0f0f]">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h1 className="text-2xl font-bold text-white">Прямые трансляции</h1>
            <Link
              href="/streams/create"
              className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
            >
              Начать трансляцию
            </Link>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : streams.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">Сейчас нет активных трансляций</p>
              <p className="text-gray-500 mt-2">Будьте первым, кто начнет трансляцию!</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {streams.map((stream) => (
                <Link
                  key={stream.id}
                  href={`/stream/${stream.id}`}
                  className="block bg-[#1a1a1a] rounded-xl overflow-hidden hover:bg-[#272727] transition-colors"
                >
                  <div className="relative aspect-video bg-gradient-to-br from-red-900 to-black">
                    <div className="absolute top-3 left-3 bg-red-600 text-white px-2 py-1 rounded text-xs font-bold flex items-center gap-1">
                      <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                      LIVE
                    </div>
                    {stream.viewers_count && (
                      <div className="absolute bottom-3 left-3 bg-black/70 text-white px-2 py-1 rounded text-xs">
                        {stream.viewers_count} зрителей
                      </div>
                    )}
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-16 h-16 bg-white/20 rounded-full flex items-center justify-center">
                        <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                        </svg>
                      </div>
                    </div>
                  </div>
                  <div className="p-4">
                    <h3 className="text-white font-medium line-clamp-2">{stream.title}</h3>
                    <p className="text-gray-400 text-sm mt-1">{stream.owner_username}</p>
                    <p className="text-gray-500 text-xs mt-2">{formatDate(stream.created_at)}</p>
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
