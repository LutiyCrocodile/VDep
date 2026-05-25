'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { searchAPI } from '@/services/api';
import { useSidebar } from '@/contexts/SidebarContext';
import { resolveMediaUrl } from '@/lib/media-url';

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

function parseDuration(value: unknown): number | undefined {
  if (value == null) return undefined;
  if (typeof value === 'number') return value;
  const s = String(value);
  if (/^\d+$/.test(s)) return parseInt(s, 10);
  const parts = s.split(':').map(Number);
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  return undefined;
}

function mapSearchHit(hit: Record<string, unknown>): Video {
  const id = String(hit.id);
  return {
    id,
    title: String(hit.title ?? ''),
    description: hit.description as string | undefined,
    thumbnail_url: resolveMediaUrl(hit.thumbnail_url as string | undefined, id),
    duration: parseDuration(hit.duration),
    views_count: Number(hit.views_count) || 0,
    created_at: String(hit.created_at ?? new Date().toISOString()),
    status: (hit.status as string) || 'ready',
  };
}

export default function SearchPage() {
  const searchParams = useSearchParams();
  const query = searchParams.get('q') || '';
  const { isCollapsed } = useSidebar();
  
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
        const data = await searchAPI.search(query, { limit: 50 });
        const hits = (data.results || []) as Record<string, unknown>[];
        setVideos(hits.map(mapSearchHit));
        setTotal(data.total || 0);
      } catch {
        setVideos([]);
        setTotal(0);
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [query]);

  return (
    <div className="min-h-screen bg-dgi-bg">
      <Header />
      <Sidebar />
      
      <main className={`pt-14 min-h-screen bg-dgi-bg transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="p-6">
          <h1 className="text-dgi-text text-xl font-bold mb-4 font-heading">
            {query ? `Результаты поиска: «${query}»` : 'Поиск'}
            {total > 0 && <span className="text-dgi-muted text-sm font-normal ml-2">({total} найдено)</span>}
          </h1>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-8 h-8 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : videos.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-dgi-muted text-lg">
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
