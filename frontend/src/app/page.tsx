'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI, searchAPI, streamsAPI } from '@/services/api';
import { resolveMediaUrl, withMediaCacheBust } from '@/lib/media-url';
import { useAuth } from '@/services/auth';
import { useSidebar } from '@/contexts/SidebarContext';

interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  duration?: number;
  views_count: number;
  created_at: string;
  user_id?: string;
  owner_username?: string;
  channel_handle?: string;
  status?: string;
  category?: string;
  classification?: string;
}

const CLASSIFICATION_FILTERS = [
  { value: 'all', label: 'Все', color: 'bg-gray-600' },
  { value: 'restricted', label: 'Личные', color: 'bg-red-600' },
];

interface LiveStreamCard {
  id: string;
  title: string;
  is_live: boolean;
  owner_username?: string;
  created_at?: string;
  thumbnail_url?: string;
  thumbnail_cache_version?: number;
  views_count?: number;
}

export default function Home() {
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get('q') || '';
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [videos, setVideos] = useState<Video[]>([]);
  const [filteredVideos, setFilteredVideos] = useState<Video[]>([]);
  const [liveStreams, setLiveStreams] = useState<LiveStreamCard[]>([]);
  const [liveLoading, setLiveLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeClassification, setActiveClassification] = useState('all');
  const { isCollapsed } = useSidebar();

  useEffect(() => {
    if (authLoading || !isAuthenticated || searchQuery.trim()) {
      setLiveStreams([]);
      return;
    }
    let cancelled = false;
    const loadLive = async () => {
      setLiveLoading(true);
      try {
        const data = await streamsAPI.getLiveStreams();
        if (!cancelled) setLiveStreams(data.streams || []);
      } catch {
        if (!cancelled) setLiveStreams([]);
      } finally {
        if (!cancelled) setLiveLoading(false);
      }
    };
    loadLive();
    const t = setInterval(loadLive, 20000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [authLoading, isAuthenticated, searchQuery]);

  useEffect(() => {
    const fetchVideos = async () => {
      setIsLoading(true);
      setError('');
      try {
        if (searchQuery.trim() && !isAuthenticated) {
          setVideos([]);
          setError('');
          return;
        }
        let data;
        if (searchQuery.trim()) {
          console.log('[Search] Using search API with query:', searchQuery);
          // Use search API for full-text search
          try {
            data = await searchAPI.search(searchQuery);
            console.log('[Search] Search API response:', data);
            const hits = data.results || [];
            setVideos(
              hits.map((hit: Record<string, unknown>) => ({
                id: String(hit.id),
                title: String(hit.title ?? ''),
                description: hit.description as string | undefined,
                thumbnail_url: resolveMediaUrl(
                  hit.thumbnail_url as string | undefined,
                  String(hit.id)
                ),
                duration:
                  typeof hit.duration === 'number'
                    ? hit.duration
                    : undefined,
                views_count: Number(hit.views_count) || 0,
                created_at: String(hit.created_at ?? ''),
                status: (hit.status as string) || 'ready',
                classification: hit.classification as string | undefined,
                owner_username: hit.owner_username as string | undefined,
              }))
            );
          } catch (searchError: any) {
            console.error('[Search] Search API failed:', searchError);
            const status = searchError?.response?.status;
            if (status === 401) {
              setError('Войдите в систему, чтобы искать видео');
            } else {
              setError('Не удалось выполнить поиск');
            }
            setVideos([]);
          }
        } else if (isAuthenticated) {
          console.log('[Search] Using regular videos API (no search query)');
          data = await videosAPI.getVideos(0, 24);
          setVideos(Array.isArray(data) ? data : (data.videos || []));
        } else {
          setVideos([]);
        }
      } catch (err: any) {
        console.error('[Search] Error fetching videos:', err);
        const errorDetail = err.response?.data?.detail || err.message || 'Не удалось загрузить видео';
        const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
        setError(errorMessage);
        setVideos([]);
      } finally {
        setIsLoading(false);
      }
    };

    if (authLoading) return;
    fetchVideos();
  }, [searchQuery, isAuthenticated, authLoading]);

  // Filter videos - only ready videos on home page, then by classification
  useEffect(() => {
    // First filter: only ready videos (exclude uploading/transcoding videos)
    let result = videos.filter(v => v.status === 'ready');
    
    // Second filter: by classification
    if (activeClassification !== 'all') {
      result = result.filter(v => v.classification === activeClassification);
    }
    
    setFilteredVideos(result);
  }, [activeClassification, videos]);

  const formatLiveDate = (dateString?: string) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleString('ru-RU');
  };

  return (
    <div className="min-h-screen bg-dgi-bg">
      <Header />
      <Sidebar />
      
      <main className={`pt-14 min-h-screen bg-dgi-bg transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="p-6">
          {!searchQuery.trim() && isAuthenticated && (
            <section className="mb-10">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-dgi-text text-xl font-semibold flex items-center gap-2 font-heading">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                  Прямые эфиры
                </h2>
                <Link href="/streams" className="text-sm text-dgi-primary hover:text-dgi-primary-mid">
                  Все трансляции →
                </Link>
              </div>
              {liveLoading && liveStreams.length === 0 ? (
                <div className="h-12 flex items-center text-dgi-muted text-sm">Загрузка эфиров…</div>
              ) : liveStreams.length === 0 ? (
                <p className="text-dgi-muted text-sm">Сейчас нет доступных вам прямых эфиров.</p>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {liveStreams.map((s) => (
                    <Link
                      key={s.id}
                      href={`/stream/${s.id}`}
                      className="block rounded-xl border border-dgi-border bg-dgi-surface overflow-hidden hover:border-dgi-primary/40 hover:shadow-md transition-all"
                    >
                      <div className="relative aspect-video bg-dgi-primary/10">
                        {s.thumbnail_url ? (
                          <img
                            src={withMediaCacheBust(
                              s.thumbnail_url,
                              s.thumbnail_cache_version || s.id
                            )}
                            alt=""
                            className="absolute inset-0 w-full h-full object-cover"
                          />
                        ) : null}
                        <div className="absolute top-2 left-2 flex items-center gap-1.5 bg-dgi-primary text-white text-xs font-semibold uppercase tracking-wide px-2 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                          Live
                        </div>
                      </div>
                      <div className="p-4">
                      <h3 className="text-dgi-text font-medium line-clamp-2">{s.title}</h3>
                      {s.owner_username && (
                        <p className="text-dgi-muted text-sm mt-2">Ведущий: {s.owner_username}</p>
                      )}
                      {s.created_at && (
                        <p className="text-dgi-muted text-xs mt-2 opacity-80">{formatLiveDate(s.created_at)}</p>
                      )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          )}

          {!searchQuery.trim() && !authLoading && !isAuthenticated && (
            <section className="mb-10 rounded-xl border border-dgi-border bg-dgi-surface p-4 shadow-sm">
              <p className="text-dgi-muted text-sm">
                <Link href="/login" className="text-dgi-primary hover:underline">
                  Войдите
                </Link>
                , чтобы видеть прямые эфиры сотрудников ДГИ на главной.
              </p>
            </section>
          )}

          {/* Classification Filters */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {CLASSIFICATION_FILTERS.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setActiveClassification(filter.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-2 ${
                  activeClassification === filter.value
                    ? `${filter.color} text-white shadow-lg`
                    : 'bg-dgi-surface-hover text-dgi-muted hover:bg-gray-200 border border-dgi-border'
                }`}
              >
                {activeClassification === filter.value && (
                  <span className="w-2 h-2 bg-white rounded-full" />
                )}
                {filter.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-10 h-10 border-3 border-dgi-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-600">{typeof error === 'string' ? error : JSON.stringify(error)}</p>
            </div>
          ) : (
            <>
              {searchQuery && (
                <h2 className="text-dgi-text text-xl font-semibold mb-6 flex items-center gap-2 font-heading">
                  <span className="w-1.5 h-6 bg-gradient-to-b from-dgi-primary to-dgi-primary-mid rounded-full"></span>
                  Результаты поиска: "{searchQuery}"
                </h2>
              )}
              {searchQuery && !isAuthenticated ? (
                <div className="text-center py-12">
                  <p className="text-dgi-muted text-lg">
                    <Link href="/login" className="text-dgi-primary hover:underline">
                      Войдите
                    </Link>
                    , чтобы искать видео
                  </p>
                </div>
              ) : filteredVideos.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-dgi-muted text-lg">
                    {searchQuery
                      ? 'По вашему запросу ничего не найдено'
                      : isAuthenticated
                        ? 'Нет доступных видео'
                        : 'Войдите, чтобы видеть видео'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                  {filteredVideos.map((video) => (
                    <VideoCard key={video.id} video={video} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
