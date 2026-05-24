'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Hls from 'hls.js';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI, videosAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';

type RelatedVideo = {
  id: string;
  title: string;
  thumbnail_url?: string;
  duration?: number;
  views_count?: number;
  owner_username?: string;
};

function teardownHls(hls: Hls | null, video: HTMLVideoElement | null) {
  if (hls) {
    try {
      hls.stopLoad();
    } catch {
      /* ignore */
    }
    try {
      hls.detachMedia();
    } catch {
      /* ignore */
    }
    try {
      hls.destroy();
    } catch {
      /* ignore */
    }
  }
  if (video) {
    try {
      video.pause();
      video.removeAttribute('src');
      video.load();
    } catch {
      /* ignore */
    }
  }
}

function formatDuration(seconds?: number) {
  if (!seconds || Number.isNaN(seconds)) return '0:00';
  const roundedSeconds = Math.floor(seconds);
  const mins = Math.floor(roundedSeconds / 60);
  const secs = roundedSeconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatViews(count: number | undefined | null) {
  const num = Number(count) || 0;
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
  return num.toString();
}

function formatDate(dateString?: string | null) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export default function LiveStreamWatchPage() {
  const params = useParams();
  const router = useRouter();
  const streamId = params.id as string;
  const { user, isLoading: authLoading } = useAuth();
  const { isCollapsed } = useSidebar();
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [ownerUsername, setOwnerUsername] = useState<string | null>(null);
  const [createdAt, setCreatedAt] = useState<string | null>(null);
  const [hlsUrl, setHlsUrl] = useState('');
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState('');
  const [relatedVideos, setRelatedVideos] = useState<RelatedVideo[]>([]);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push('/login');
      return;
    }

    let cancelled = false;

    const refresh = async () => {
      try {
        const s = await streamsAPI.getStream(streamId);
        if (cancelled) return;
        setTitle(s.title || '');
        setDescription(s.description || '');
        setOwnerUsername(s.owner_username || null);
        setCreatedAt(s.created_at || null);
        setHlsUrl(s.hls_url || '');
        setIsLive(!!s.is_live);
        if (!s.is_live && s.end_time) {
          setError('');
        }
      } catch (e: unknown) {
        if (cancelled) return;
        const err = e as { response?: { data?: { detail?: string } } };
        setError(err.response?.data?.detail || 'Нет доступа к трансляции');
      }
    };

    refresh();
    const interval = setInterval(refresh, 2000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [streamId, user, authLoading, router]);

  useEffect(() => {
    if (!user) return;
    (async () => {
      try {
        const data = await videosAPI.getVideos(0, 10);
        setRelatedVideos(
          (data.videos || [])
            .filter((v: RelatedVideo) => v.id !== streamId)
            .slice(0, 8)
        );
      } catch {
        setRelatedVideos([]);
      }
    })();
  }, [user, streamId]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !hlsUrl || !isLive) {
      teardownHls(hlsRef.current, el);
      hlsRef.current = null;
      return;
    }

    teardownHls(hlsRef.current, el);
    hlsRef.current = null;

    const onVideoError = (ev: Event) => {
      const ve = ev.target as HTMLVideoElement;
      const code = ve?.error?.code;
      if (code === MediaError.MEDIA_ERR_ABORTED) {
        ev.preventDefault();
      }
    };
    el.addEventListener('error', onVideoError);

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      });
      hlsRef.current = hls;
      hls.loadSource(hlsUrl);
      hls.attachMedia(el);
      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        el.play().catch(() => undefined);
      });
      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          setError('Трансляция временно недоступна. Попробуйте обновить страницу через несколько секунд.');
        }
      });
    } else if (el.canPlayType('application/vnd.apple.mpegurl')) {
      el.src = hlsUrl;
      el.play().catch(() => undefined);
    } else {
      setError('Браузер не поддерживает воспроизведение трансляции');
    }

    return () => {
      el.removeEventListener('error', onVideoError);
      teardownHls(hlsRef.current, el);
      hlsRef.current = null;
    };
  }, [hlsUrl, isLive]);

  if (!user && !authLoading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-dgi-bg">
      <Header />
      <Sidebar />
      <main
        className={`pt-14 min-h-screen bg-dgi-bg transition-all duration-300 ease-in-out ${
          isCollapsed ? 'ml-0' : 'ml-64'
        }`}
      >
        <div className="flex gap-6 p-6">
          <div className="flex-1 max-w-5xl">
            <div className="aspect-video bg-black rounded-xl overflow-hidden border border-dgi-border shadow-md relative">
              {isLive ? (
                <video ref={videoRef} className="w-full h-full" controls playsInline />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-dgi-surface-hover">
                  <p className="text-dgi-muted text-sm px-6 text-center">Эфир завершён</p>
                </div>
              )}
              {isLive && (
                <div className="absolute top-3 left-3 inline-flex items-center gap-2 bg-dgi-primary text-white px-3 py-1 rounded-full text-sm font-semibold shadow-md">
                  <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                  LIVE
                </div>
              )}
            </div>

            {error && (
              <p className="text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mt-4 text-sm">
                {error}
              </p>
            )}

            <div className="mt-6">
              <h1 className="text-2xl font-bold text-dgi-text font-heading">{title || 'Трансляция'}</h1>

              <div className="flex items-center gap-4 mt-4">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-lg shadow-lg">
                  {ownerUsername?.[0]?.toUpperCase() || 'U'}
                </div>
                <div>
                  <p className="text-dgi-text font-semibold">{ownerUsername || 'Ведущий'}</p>
                  {createdAt && (
                    <p className="text-dgi-muted text-sm">Начало эфира • {formatDate(createdAt)}</p>
                  )}
                </div>
              </div>

              <div className="mt-4 bg-dgi-surface border border-dgi-border rounded-xl p-5">
                <p className="text-dgi-text text-sm leading-relaxed whitespace-pre-wrap">
                  {description || 'Описание отсутствует'}
                </p>
              </div>
            </div>
          </div>

          <div className="w-96 flex-shrink-0 hidden lg:block">
            <h3 className="text-dgi-text font-semibold mb-4 text-lg font-heading">Рекомендуемые видео</h3>
            <div className="space-y-4">
              {relatedVideos.length === 0 ? (
                <p className="text-dgi-muted text-sm">Пока нет других видео</p>
              ) : (
                relatedVideos.map((v) => (
                  <Link key={v.id} href={`/watch?v=${v.id}`} className="flex gap-3 group">
                    <div className="relative w-40 aspect-video rounded-xl overflow-hidden bg-dgi-surface border border-dgi-border flex-shrink-0 group-hover:border-dgi-primary/30 transition-all duration-200">
                      <img
                        src={
                          v.thumbnail_url ||
                          `https://via.placeholder.com/160x90/1a1a3e/FFFFFF?text=${encodeURIComponent(
                            v.title.substring(0, 15)
                          )}`
                        }
                        alt={v.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      />
                      {v.duration != null && (
                        <div className="absolute bottom-1.5 right-1.5 bg-dgi-bg/90 text-white text-xs px-1.5 py-0.5 rounded font-medium">
                          {formatDuration(v.duration)}
                        </div>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="text-dgi-text text-sm font-medium line-clamp-2 group-hover:text-dgi-primary transition-colors duration-200">
                        {v.title}
                      </h4>
                      <p className="text-dgi-muted text-xs mt-1">{v.owner_username}</p>
                      <p className="text-dgi-muted text-xs opacity-80">
                        {formatViews(v.views_count)} просмотров
                      </p>
                    </div>
                  </Link>
                ))
              )}
            </div>
          </div>
        </div>

        <div className="lg:hidden px-6 pb-8">
          <h3 className="text-dgi-text font-semibold mb-4 text-lg font-heading">Рекомендуемые видео</h3>
          <div className="space-y-4">
            {relatedVideos.map((v) => (
              <Link key={v.id} href={`/watch?v=${v.id}`} className="flex gap-3 group">
                <div className="relative w-36 aspect-video rounded-xl overflow-hidden bg-dgi-surface border border-dgi-border flex-shrink-0">
                  <img
                    src={v.thumbnail_url || `https://via.placeholder.com/160x90`}
                    alt={v.title}
                    className="w-full h-full object-cover"
                  />
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-dgi-text text-sm font-medium line-clamp-2">{v.title}</h4>
                  <p className="text-dgi-muted text-xs mt-1">{v.owner_username}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
