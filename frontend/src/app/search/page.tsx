'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { searchAPI } from '@/services/api';

interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  duration?: number;
  views_count: number;
  created_at: string;
  owner_username?: string;
  status?: string;
  highlights?: string[];
}

export default function SearchPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  
  const [videos, setVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    const fetchResults = async () => {
      if (!query) {
        setVideos([]);
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const data = await searchAPI.search(query);
        setVideos(data.results || []);
        setTotal(data.total || 0);
      } catch {
        // Mock data
        setVideos([
          {
            id: '1',
            title: `Результат поиска: ${query}`,
            description: 'Найдено по запросу',
            views_count: 1000,
            created_at: new Date().toISOString(),
            owner_username: 'Администратор',
            duration: 300,
            status: 'ready',
          },
        ]);
        setTotal(1);
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [query]);

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Header />
      <Sidebar />
      
      <main className="ml-64 pt-14 min-h-screen bg-[#0f0f0f]">
        <div className="p-6">
          <h1 className="text-white text-xl mb-4">
            {query ? `Результаты поиска: "${query}"` : 'Поиск'}
            {total > 0 && <span className="text-gray-400 text-sm ml-2">({total} найдено)</span>}
          </h1>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-lg">
                {query ? 'Ничего не найдено' : 'Введите запрос для поиска'}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {videos.map((video) => (
                <VideoCard key={video.id} video={video} />
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
