'use client';

import Link from 'next/link';
import { useState } from 'react';

interface VideoCardProps {
  video: {
    id: string;
    title: string;
    description?: string;
    thumbnail_url?: string;
    duration?: number;
    views_count: number;
    created_at: string;
    owner_username?: string;
    status?: string;
  };
}

export default function VideoCard({ video }: VideoCardProps) {
  const [imageError, setImageError] = useState(false);

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
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - date.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays < 1) return 'сегодня';
    if (diffDays === 1) return 'вчера';
    if (diffDays < 7) return `${diffDays} дней назад`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} недель назад`;
    if (diffDays < 365) return `${Math.floor(diffDays / 30)} месяцев назад`;
    return `${Math.floor(diffDays / 365)} лет назад`;
  };

  const thumbnailUrl = video.thumbnail_url && !imageError
    ? video.thumbnail_url
    : `https://via.placeholder.com/320x180/272727/FFFFFF?text=${encodeURIComponent(video.title.substring(0, 20))}`;

  return (
    <Link href={`/watch?v=${video.id}`} className="group block">
      <div className="relative aspect-video rounded-xl overflow-hidden bg-[#1a1a3e] border border-[#27274a] group-hover:border-indigo-500/30 transition-all duration-300">
        <img
          src={thumbnailUrl}
          alt={video.title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          onError={() => setImageError(true)}
        />
        {video.duration && (
          <div className="absolute bottom-2 right-2 bg-[#0a0a1a]/90 text-white text-xs px-2 py-1 rounded-lg font-medium">
            {formatDuration(video.duration)}
          </div>
        )}
        {video.status === 'processing' && (
          <div className="absolute inset-0 bg-[#0a0a1a]/80 flex items-center justify-center backdrop-blur-sm">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-white text-sm font-medium">Обработка...</span>
            </div>
          </div>
        )}
      </div>
      <div className="mt-3 flex gap-3">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-medium text-sm flex-shrink-0 shadow-lg shadow-indigo-500/20">
          {video.owner_username?.[0]?.toUpperCase() || 'U'}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-white font-medium text-sm line-clamp-2 leading-tight group-hover:text-indigo-400 transition-colors duration-200">
            {video.title}
          </h3>
          <p className="text-zinc-400 text-sm mt-1 hover:text-zinc-300 transition-colors duration-200">
            {video.owner_username || 'Неизвестный'}
          </p>
          <p className="text-zinc-500 text-xs mt-0.5">
            {formatViews(video.views_count)} просмотров • {formatDate(video.created_at)}
          </p>
        </div>
      </div>
    </Link>
  );
}
