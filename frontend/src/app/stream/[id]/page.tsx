'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Hls from 'hls.js';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

/** Корректное отключение HLS без AbortError в overlay при уходе со страницы / смене URL. */
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

export default function LiveStreamWatchPage() {
  const params = useParams();
  const router = useRouter();
  const streamId = params.id as string;
  const { user, isLoading: authLoading } = useAuth();
  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  const [title, setTitle] = useState('');
  const [hlsUrl, setHlsUrl] = useState('');
  const [isLive, setIsLive] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      router.push('/login');
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const s = await streamsAPI.getStream(streamId);
        if (cancelled) return;
        setTitle(s.title);
        setHlsUrl(s.hls_url || '');
        setIsLive(!!s.is_live);
      } catch (e: unknown) {
        const err = e as { response?: { data?: { detail?: string } } };
        setError(err.response?.data?.detail || 'Нет доступа к трансляции');
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [streamId, user, authLoading, router]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el || !hlsUrl) return;

    teardownHls(hlsRef.current, el);
    hlsRef.current = null;

    const onVideoError = (ev: Event) => {
      const ve = ev.target as HTMLVideoElement;
      const code = ve?.error?.code;
      // MEDIA_ERR_ABORTED — нормально при смене src / выгрузке страницы
      if (code === MediaError.MEDIA_ERR_ABORTED) {
        ev.preventDefault();
        return;
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
          setError('Ошибка воспроизведения HLS. Убедитесь, что эфир запущен в OBS.');
        }
      });
    } else if (el.canPlayType('application/vnd.apple.mpegurl')) {
      el.src = hlsUrl;
      el.play().catch(() => undefined);
    } else {
      setError('Браузер не поддерживает HLS');
    }

    return () => {
      el.removeEventListener('error', onVideoError);
      teardownHls(hlsRef.current, el);
      hlsRef.current = null;
    };
  }, [hlsUrl]);

  if (!user && !authLoading) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Header />
      <Sidebar />
      <main className="pt-16 ml-0 md:ml-64 p-6 max-w-5xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-2">{title || 'Трансляция'}</h1>
        {isLive && (
          <div className="mb-4 inline-flex items-center gap-2 bg-red-600 text-white px-3 py-1 rounded text-sm font-semibold">
            <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
            LIVE
          </div>
        )}
        {error && <p className="text-red-400 mb-4">{typeof error === 'string' ? error : JSON.stringify(error)}</p>}
        <div className="aspect-video bg-black rounded-xl overflow-hidden border border-gray-800">
          <video ref={videoRef} className="w-full h-full" controls playsInline />
        </div>
        <p className="text-gray-500 text-sm mt-4">
          Если картинки нет: нажмите «Разрешить эфир» на странице «Запустить трансляцию», затем начните трансляцию в OBS.
        </p>
      </main>
    </div>
  );
}
