'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Hls from 'hls.js';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI, videosAPI, channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';
import { withMediaCacheBust } from '@/lib/media-url';

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
  const [streamOwnerId, setStreamOwnerId] = useState<string | null>(null);
  const [channelId, setChannelId] = useState<string | null>(null);
  const [channelHandle, setChannelHandle] = useState<string | null>(null);
  const [streamLoaded, setStreamLoaded] = useState(false);
  const [likesCount, setLikesCount] = useState(0);
  const [userLiked, setUserLiked] = useState(false);
  const [viewersCount, setViewersCount] = useState(0);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [error, setError] = useState('');
  const [relatedVideos, setRelatedVideos] = useState<RelatedVideo[]>([]);
  const [thumbnailUrl, setThumbnailUrl] = useState<string | null>(null);
  const [thumbnailCacheBust, setThumbnailCacheBust] = useState<number>(0);
  const [archivedVideoId, setArchivedVideoId] = useState<string | null>(null);

  const isOwner = Boolean(user?.id && streamOwnerId && user.id === streamOwnerId);
  const channelUrl =
    channelHandle
      ? `/channel/${channelHandle}`
      : ownerUsername
        ? `/channel/${ownerUsername}`
        : null;

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
        setStreamOwnerId(s.user_id || null);
        setChannelId(s.channel_id || null);
        setChannelHandle(s.channel_handle || null);
        setLikesCount(s.likes_count ?? 0);
        setUserLiked(!!s.user_liked);
        setViewersCount(s.viewers_count ?? 0);
        setHlsUrl(s.hls_url || '');
        setThumbnailUrl(s.thumbnail_url || null);
        const cacheVer =
          (s.thumbnail_cache_version as number | undefined) ||
          (s.thumbnail_url ? Date.now() : 0);
        setThumbnailCacheBust(cacheVer);
        setArchivedVideoId(s.archived_video_id || null);
        const ended = Boolean(s.end_time);
        setIsLive(!ended && (!!s.is_live || !!s.start_time));
        setStreamLoaded(true);
        setError('');
        if (s.channel_id && user?.id && s.user_id !== user.id) {
          try {
            const sub = await channelsAPI.isSubscribed(s.channel_id);
            setIsSubscribed(sub.is_subscribed);
          } catch {
            /* optional */
          }
        }
      } catch (e: unknown) {
        if (cancelled) return;
        setStreamLoaded(false);
        const err = e as { response?: { status?: number; data?: { detail?: string } } };
        const status = err.response?.status;
        const detail = err.response?.data?.detail;
        if (status === 403) {
          setError(detail || 'Нет доступа к трансляции');
        } else if (status === 404) {
          setError(detail || 'Трансляция не найдена');
        } else {
          setError(detail || 'Не удалось загрузить трансляцию. Обновите страницу.');
        }
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
    if (!user || authLoading) return;
    let cancelled = false;

    const heartbeat = async () => {
      try {
        const data = await streamsAPI.sendPresence(streamId);
        if (!cancelled) setViewersCount(data.viewers_count ?? 0);
      } catch {
        /* ignore */
      }
    };

    heartbeat();
    const interval = setInterval(heartbeat, 20000);

    return () => {
      cancelled = true;
      clearInterval(interval);
      streamsAPI.leavePresence(streamId).catch(() => undefined);
    };
  }, [streamId, user, authLoading]);

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

  const handleLike = async () => {
    try {
      if (userLiked) {
        const data = await streamsAPI.unlikeStream(streamId);
        setUserLiked(data.user_liked);
        setLikesCount(data.likes_count);
      } else {
        const data = await streamsAPI.likeStream(streamId);
        setUserLiked(data.user_liked);
        setLikesCount(data.likes_count);
      }
    } catch (err) {
      console.error('Like stream error', err);
    }
  };

  const handleSubscribe = async () => {
    if (!channelId || isOwner) return;
    try {
      if (isSubscribed) {
        await channelsAPI.unsubscribe(channelId);
        setIsSubscribed(false);
      } else {
        await channelsAPI.subscribe(channelId);
        setIsSubscribed(true);
      }
    } catch (err) {
      console.error('Subscribe error', err);
    }
  };

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
              {thumbnailUrl && (
                <img
                  src={withMediaCacheBust(thumbnailUrl, thumbnailCacheBust || streamId)}
                  alt=""
                  className={`absolute inset-0 w-full h-full object-cover ${isLive ? 'z-0' : 'z-[1]'}`}
                />
              )}
              {isLive ? (
                <video
                  ref={videoRef}
                  className="relative z-[2] w-full h-full object-cover bg-black/40"
                  controls
                  playsInline
                  poster={
                    thumbnailUrl
                      ? withMediaCacheBust(thumbnailUrl, thumbnailCacheBust || streamId)
                      : undefined
                  }
                />
              ) : (
                <div className="absolute inset-0 z-[2] flex flex-col items-center justify-center bg-black/50 px-6 text-center">
                  <p className="text-white text-sm font-medium mb-2">Эфир завершён</p>
                  {archivedVideoId && (
                    <Link
                      href={`/watch?v=${archivedVideoId}`}
                      className="text-dgi-primary-mid hover:underline text-sm"
                    >
                      Смотреть запись на канале
                    </Link>
                  )}
                </div>
              )}
              <div className="absolute top-3 left-3 flex flex-wrap gap-2">
                {isLive && (
                  <div className="inline-flex items-center gap-2 bg-dgi-primary text-white px-3 py-1 rounded-full text-sm font-semibold shadow-md">
                    <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                    LIVE
                  </div>
                )}
                {isLive && (
                  <div className="inline-flex items-center gap-1.5 bg-black/70 text-white px-3 py-1 rounded-full text-sm font-medium shadow-md">
                    <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                      <path
                        fillRule="evenodd"
                        d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z"
                        clipRule="evenodd"
                      />
                    </svg>
                    {formatViews(viewersCount)} зрителей
                  </div>
                )}
              </div>
            </div>

            {error && (
              <p className="text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 mt-4 text-sm">
                {error}
              </p>
            )}

            {streamLoaded && (
              <div className="mt-6">
                <h1 className="text-2xl font-bold text-dgi-text font-heading">{title || 'Трансляция'}</h1>

                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mt-4 gap-4">
                  <div className="flex items-center gap-4 min-w-0 flex-wrap">
                    {channelUrl ? (
                      <Link
                        href={channelUrl}
                        className="w-12 h-12 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)] transition-all flex-shrink-0"
                      >
                        {ownerUsername?.[0]?.toUpperCase() || 'U'}
                      </Link>
                    ) : (
                      <div className="w-12 h-12 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-lg shadow-lg flex-shrink-0">
                        {ownerUsername?.[0]?.toUpperCase() || 'U'}
                      </div>
                    )}
                    <div className="min-w-0">
                      {channelUrl ? (
                        <Link
                          href={channelUrl}
                          className="text-dgi-text font-semibold hover:text-dgi-primary transition-colors block truncate"
                        >
                          {ownerUsername || 'Ведущий'}
                        </Link>
                      ) : (
                        <p className="text-dgi-text font-semibold">{ownerUsername || 'Ведущий'}</p>
                      )}
                      <p className="text-dgi-muted text-sm">
                        {isLive
                          ? `${formatViews(viewersCount)} зрителей сейчас`
                          : viewersCount > 0
                            ? `Пик зрителей: ${formatViews(viewersCount)}`
                            : '0 зрителей'}
                        {' • '}
                        {formatViews(likesCount)} лайков
                        {createdAt ? ` • ${formatDate(createdAt)}` : ''}
                      </p>
                    </div>
                    {channelId && !isOwner && (
                      <button
                        type="button"
                        onClick={handleSubscribe}
                        className={`px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 shadow-lg flex-shrink-0 ${
                          isSubscribed
                            ? 'bg-dgi-surface-hover text-dgi-text border border-dgi-border hover:bg-gray-200'
                            : 'bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:opacity-90 text-white shadow-[0_4px_14px_rgba(200,20,30,0.15)]'
                        }`}
                      >
                        {isSubscribed ? 'Подписан' : 'Подписаться'}
                      </button>
                    )}
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    <button
                      type="button"
                      onClick={handleLike}
                      className={`flex items-center gap-2 px-5 py-2.5 rounded-full transition-all duration-200 border ${
                        userLiked
                          ? 'bg-gradient-to-r from-dgi-primary to-dgi-primary-mid border-transparent text-white'
                          : 'bg-dgi-surface hover:bg-dgi-surface-hover text-dgi-text border-dgi-border hover:border-dgi-primary/30'
                      }`}
                    >
                      <svg
                        className={`w-5 h-5 ${userLiked ? 'text-white' : 'text-dgi-primary'}`}
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                      </svg>
                      <span className="font-medium">
                        Нравится{likesCount > 0 ? ` (${formatViews(likesCount)})` : ''}
                      </span>
                    </button>
                  </div>
                </div>

                <div className="mt-4 bg-dgi-surface border border-dgi-border rounded-xl p-5">
                  <p className="text-dgi-text text-sm leading-relaxed whitespace-pre-wrap">
                    {description || 'Описание отсутствует'}
                  </p>
                </div>
              </div>
            )}
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
