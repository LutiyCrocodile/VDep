'use client';

import Link from 'next/link';
import { useState, useEffect } from 'react';
import { videosAPI } from '@/services/api';
import { resolveMediaUrl } from '@/lib/media-url';

interface VideoCardProps {
  video: {
    id: string;
    title: string;
    description?: string;
    thumbnail_url?: string;
    duration?: number;
    views_count?: number;
    created_at: string;
    user_id?: string;
    owner_username?: string;
    channel_handle?: string;
    channel_id?: string;
    status?: string;
    transcoding_progress?: number;
    classification?: string;
  };
}

export default function VideoCard({ video }: VideoCardProps) {
  const [imageError, setImageError] = useState(false);
  const [localProgress, setLocalProgress] = useState(video.transcoding_progress || 0);
  const [localStatus, setLocalStatus] = useState(video.status);
  
  // Update local state when props change
  useEffect(() => {
    setLocalProgress(video.transcoding_progress || 0);
    setLocalStatus(video.status);
  }, [video.transcoding_progress, video.status]);
  
  // Polling for transcoding progress
  useEffect(() => {
    if (localStatus !== 'transcoding' && localStatus !== 'uploaded') return;
    
    const interval = setInterval(async () => {
      try {
        const updatedVideo = await videosAPI.getVideo(video.id);
        console.log('Polling video status:', updatedVideo.status, 'progress:', updatedVideo.transcoding_progress);
        setLocalStatus(updatedVideo.status);
        setLocalProgress(updatedVideo.transcoding_progress || 0);
        
        // Stop polling if video is ready or failed
        if (updatedVideo.status === 'ready' || updatedVideo.status === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Failed to poll video status:', err);
      }
    }, 2000); // Poll every 2 seconds
    
    return () => clearInterval(interval);
  }, [video.id, localStatus]);
  
  // Debug logging
  console.log('VideoCard video data:', video.id, 'status:', localStatus, 'progress:', localProgress);

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViews = (count: number | undefined | null) => {
    const num = Number(count) || 0;
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHours = Math.floor(diffMin / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffSec < 60) return 'только что';
    if (diffMin < 60) return `${diffMin} мин. назад`;
    if (diffHours < 24) return `${diffHours} ч. назад`;
    if (diffDays === 0) return 'сегодня';
    if (diffDays === 1) return 'вчера';
    if (diffDays < 7) return `${diffDays} дн. назад`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} нед. назад`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} мес. назад`;
    return `${Math.floor(diffDays / 365)} г. назад`;
  };

  const getClassificationBadge = () => {
    if (!video.classification || video.classification === 'public') return null;

    const badges = {
      restricted: { text: 'Личное', color: 'bg-red-600/70' },
      confidential: { text: 'Конфиденциальное', color: 'bg-yellow-600/70' },
      internal: { text: 'Внутреннее', color: 'bg-dgi-primary/70' },
    };

    const badge = badges[video.classification as keyof typeof badges];
    if (!badge) return null;

    return (
      <div className={`absolute top-2 left-2 ${badge.color} text-white text-xs px-2 py-1 rounded-lg font-medium opacity-80 group-hover:opacity-0 transition-opacity duration-100`}>
        {badge.text}
      </div>
    );
  };

  const getThumbnailUrl = () => {
    const resolved = resolveMediaUrl(video.thumbnail_url, video.id);
    if (resolved) return resolved;
    const encodedTitle = video.title ? encodeURIComponent(video.title.substring(0, 15)) : 'Video';
    return `https://placehold.co/320x180/1a1a3e/FFFFFF/png?text=${encodedTitle}`;
  };
  
  const thumbnailUrl = !imageError ? getThumbnailUrl() : `https://placehold.co/320x180/272727/FFFFFF/png?text=No+Image`;

  return (
    <Link href={`/watch?v=${video.id}`} className="group block">
      <div className="relative aspect-video rounded-xl overflow-hidden bg-dgi-surface border border-dgi-border group-hover:border-dgi-primary/30 transition-all duration-300">
        {getClassificationBadge()}
        <img
          src={thumbnailUrl}
          alt={video.title || 'Video'}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          onError={() => setImageError(true)}
        />
        {video.duration && (
          <div className="absolute bottom-2 right-2 bg-black/75 text-white text-xs px-2 py-1 rounded-lg font-medium">
            {formatDuration(video.duration)}
          </div>
        )}
        {(localStatus === 'uploaded' || localStatus === 'uploading') && (
          <div className="absolute inset-0 bg-dgi-bg/80 flex items-center justify-center backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 border-2 border-yellow-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-white text-sm font-medium">Ожидание обработки...</span>
            </div>
          </div>
        )}
        {localStatus === 'transcoding' && (
          <div className="absolute inset-0 bg-dgi-bg/90 flex flex-col items-center justify-center backdrop-blur-sm px-4">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-5 h-5 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-white text-sm font-medium">Обработка...</span>
            </div>
            <div className="w-full max-w-[120px] h-2 bg-gray-300 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-dgi-primary to-dgi-primary-mid transition-all duration-300"
                style={{ width: `${localProgress}%` }}
              />
            </div>
            <span className="text-dgi-muted text-xs mt-1">{localProgress}%</span>
          </div>
        )}
      </div>
      <div className="mt-3 flex gap-3">
        <Link
          href={video.channel_handle ? `/channel/${video.channel_handle}` : (video.owner_username ? `/channel/${video.owner_username}` : '#')}
          className="w-9 h-9 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-medium text-sm flex-shrink-0 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] hover:shadow-[0_4px_14px_rgba(200,20,30,0.35)] transition-all"
          onClick={(e) => e.stopPropagation()}
        >
          {video.owner_username?.[0]?.toUpperCase() || 'U'}
        </Link>
        <div className="flex-1 min-w-0">
          <h3 className="text-dgi-text font-medium text-sm line-clamp-2 leading-tight group-hover:text-dgi-primary transition-colors duration-200">
            {video.title || 'Без названия'}
          </h3>
          <Link
            href={video.channel_handle ? `/channel/${video.channel_handle}` : (video.owner_username ? `/channel/${video.owner_username}` : '#')}
            className="text-dgi-muted text-sm mt-1 hover:text-dgi-primary transition-colors duration-200 block"
            onClick={(e) => e.stopPropagation()}
          >
            {video.owner_username || 'Неизвестный'}
          </Link>
          <p className="text-dgi-muted text-xs mt-0.5">
            {formatViews(video.views_count)} просмотров • {formatDate(video.created_at)}
          </p>
        </div>
      </div>
    </Link>
  );
}
