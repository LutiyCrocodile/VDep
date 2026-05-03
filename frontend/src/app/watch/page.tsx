'use client';

import { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI } from '@/services/api';
import Link from 'next/link';

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
  hls_url?: string;
  qualities?: { quality: string; url: string }[];
}

export default function WatchPage() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get('v');
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const [video, setVideo] = useState<Video | null>(null);
  const [relatedVideos, setRelatedVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [currentQuality, setCurrentQuality] = useState('auto');
  const [showQualityMenu, setShowQualityMenu] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const fetchVideo = async () => {
      if (!videoId) return;
      
      try {
        const data = await videosAPI.getVideo(videoId);
        setVideo(data);
      } catch (err) {
        setError('Видео не найдено');
        // Mock data
        setVideo({
          id: videoId,
          title: 'Демо видео - Обзор системы',
          description: 'Это демонстрационное видео для тестирования интерфейса.',
          views_count: 1500,
          created_at: new Date().toISOString(),
          owner_username: 'Администратор',
          duration: 600,
          status: 'ready',
          hls_url: '',
        });
      } finally {
        setIsLoading(false);
      }
    };

    const fetchRelated = async () => {
      try {
        const data = await videosAPI.getVideos(0, 10);
        setRelatedVideos((data.videos || []).filter((v: Video) => v.id !== videoId).slice(0, 8));
      } catch {
        setRelatedVideos([
          {
            id: '2',
            title: 'Совещание отдела имущества - 2024',
            views_count: 890,
            created_at: new Date(Date.now() - 86400000).toISOString(),
            owner_username: 'Менеджер',
            duration: 3600,
            status: 'ready',
          },
          {
            id: '3',
            title: 'Инструкция по работе с системой',
            views_count: 2100,
            created_at: new Date(Date.now() - 172800000).toISOString(),
            owner_username: 'HR',
            duration: 900,
            status: 'ready',
          },
        ]);
      }
    };

    fetchVideo();
    fetchRelated();
  }, [videoId]);

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViews = (count: number) => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0a0a1a]">
        <Header />
        <div className="flex items-center justify-center h-screen">
          <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="min-h-screen bg-[#0a0a1a]">
        <Header />
        <div className="flex flex-col items-center justify-center h-screen">
          <p className="text-white text-xl">{error || 'Видео не найдено'}</p>
          <Link href="/" className="mt-4 text-indigo-400 hover:text-indigo-300 transition-colors">
            Вернуться на главную
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a1a]">
      <Header />
      <Sidebar />
      
      <main className="ml-64 pt-14 min-h-screen bg-[#0a0a1a]">
        <div className="flex gap-6 p-6">
          {/* Main content */}
          <div className="flex-1 max-w-5xl">
            {/* Video Player */}
            <div className="relative aspect-video bg-black rounded-2xl overflow-hidden group border border-[#27274a] shadow-2xl shadow-indigo-500/10">
              <video
                ref={videoRef}
                className="w-full h-full"
                poster={video.thumbnail_url || `https://via.placeholder.com/1280x720/1a1a3e/FFFFFF?text=${encodeURIComponent(video.title)}`}
                onClick={() => setIsPlaying(!isPlaying)}
                onTimeUpdate={(e) => setCurrentTime(e.currentTarget.currentTime)}
              >
                <source src={video.hls_url || video.qualities?.[0]?.url || ''} type="application/x-mpegURL" />
              </video>
              
              {/* Play button overlay */}
              {!isPlaying && (
                <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a1a]/60 backdrop-blur-sm">
                  <button 
                    onClick={() => setIsPlaying(true)}
                    className="w-24 h-24 bg-gradient-to-br from-indigo-500 to-violet-600 rounded-full flex items-center justify-center hover:from-indigo-400 hover:to-violet-500 transition-all duration-300 shadow-lg shadow-indigo-500/40 hover:shadow-indigo-500/60 hover:scale-110"
                  >
                    <svg className="w-12 h-12 text-white ml-1" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Controls overlay */}
              <div className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0a0a1a] via-[#0a0a1a]/80 to-transparent p-6 transition-opacity duration-300 ${showControls ? 'opacity-100' : 'opacity-0'}`}>
                {/* Progress bar */}
                <div className="w-full h-1.5 bg-[#27274a] rounded-full cursor-pointer mb-4 group/progress">
                  <div 
                    className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full relative"
                    style={{ width: `${(currentTime / (video.duration || 1)) * 100}%` }}
                  >
                    <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full opacity-0 group-hover/progress:opacity-100 transition-opacity" />
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="hover:bg-white/10 rounded-full p-2 transition-colors"
                    >
                      {isPlaying ? (
                        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                        </svg>
                      )}
                    </button>
                    <span className="text-white text-sm font-medium">{formatDuration(currentTime)} / {formatDuration(video.duration)}</span>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {/* Quality selector */}
                    <div className="relative">
                      <button 
                        onClick={() => setShowQualityMenu(!showQualityMenu)}
                        className="px-3 py-1 bg-[#1a1a3e]/80 hover:bg-[#252550] text-white text-sm rounded-lg transition-colors border border-[#27274a]"
                      >
                        {currentQuality === 'auto' ? 'Авто' : currentQuality}
                      </button>
                      {showQualityMenu && (
                        <div className="absolute bottom-full right-0 mb-2 bg-[#1a1a3e] border border-[#27274a] rounded-xl overflow-hidden shadow-xl min-w-[120px]">
                          {['auto', '1080p', '720p', '480p', '360p'].map((quality) => (
                            <button
                              key={quality}
                              onClick={() => { setCurrentQuality(quality); setShowQualityMenu(false); }}
                              className={`w-full px-4 py-2 text-sm text-left transition-colors ${
                                currentQuality === quality 
                                  ? 'bg-gradient-to-r from-indigo-600/30 to-violet-600/30 text-white' 
                                  : 'text-zinc-400 hover:bg-[#252550] hover:text-white'
                              }`}
                            >
                              {quality === 'auto' ? 'Авто' : quality}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    {/* Volume */}
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                      </svg>
                      <div className="w-16 h-1 bg-[#27274a] rounded-full">
                        <div className="h-full w-2/3 bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full" />
                      </div>
                    </div>
                    
                    {/* Fullscreen */}
                    <button className="hover:bg-white/10 rounded-full p-2 transition-colors">
                      <svg className="w-5 h-5 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Video info */}
            <div className="mt-6">
              <h1 className="text-2xl font-bold text-white">{video.title}</h1>
              
              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-500/20">
                    {video.owner_username?.[0]?.toUpperCase() || 'U'}
                  </div>
                  <div>
                    <p className="text-white font-semibold">{video.owner_username || 'Неизвестный'}</p>
                    <p className="text-zinc-400 text-sm">{formatViews(video.views_count)} просмотров • {formatDate(video.created_at)}</p>
                  </div>
                  <button className="ml-4 bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40">
                    Подписаться
                  </button>
                </div>
                
                <div className="flex items-center gap-3">
                  <button className="flex items-center gap-2 bg-[#1a1a3e] hover:bg-[#252550] text-white px-5 py-2.5 rounded-full transition-all duration-200 border border-[#27274a] hover:border-indigo-500/30">
                    <svg className="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                    </svg>
                    <span className="font-medium">Нравится</span>
                  </button>
                  <button className="flex items-center gap-2 bg-[#1a1a3e] hover:bg-[#252550] text-white px-5 py-2.5 rounded-full transition-all duration-200 border border-[#27274a] hover:border-indigo-500/30">
                    <svg className="w-5 h-5 text-violet-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                    </svg>
                    <span className="font-medium">Поделиться</span>
                  </button>
                </div>
              </div>

              {/* Description */}
              <div className="mt-4 bg-[#1a1a3e] border border-[#27274a] rounded-xl p-5">
                <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{video.description || 'Описание отсутствует'}</p>
              </div>
            </div>
          </div>

          {/* Related videos */}
          <div className="w-96 flex-shrink-0">
            <h3 className="text-white font-semibold mb-4 text-lg">Похожие видео</h3>
            <div className="space-y-4">
              {relatedVideos.map((v) => (
                <Link key={v.id} href={`/watch?v=${v.id}`} className="flex gap-3 group">
                  <div className="relative w-40 aspect-video rounded-xl overflow-hidden bg-[#1a1a3e] border border-[#27274a] flex-shrink-0 group-hover:border-indigo-500/30 transition-all duration-200">
                    <img 
                      src={v.thumbnail_url || `https://via.placeholder.com/160x90/1a1a3e/FFFFFF?text=${encodeURIComponent(v.title.substring(0, 15))}`}
                      alt={v.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    {v.duration && (
                      <div className="absolute bottom-1.5 right-1.5 bg-[#0a0a1a]/90 text-white text-xs px-1.5 py-0.5 rounded font-medium">
                        {formatDuration(v.duration)}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-white text-sm font-medium line-clamp-2 group-hover:text-indigo-400 transition-colors duration-200">
                      {v.title}
                    </h4>
                    <p className="text-zinc-400 text-xs mt-1">{v.owner_username}</p>
                    <p className="text-zinc-500 text-xs">{formatViews(v.views_count)} просмотров</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
