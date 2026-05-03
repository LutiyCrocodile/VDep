'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

export default function LikedPage() {
  const { user } = useAuth();
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLiked = async () => {
      if (user) {
        try {
          const data = await videosAPI.getVideos();
          setVideos(data.videos || []);
        } catch (err) {
          console.error('Failed to fetch liked videos:', err);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchLiked();
  }, [user]);

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <main className="ml-64 pt-14 min-h-screen flex items-center justify-center">
          <p className="text-white">Войдите для просмотра</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
      <Header />
      <Sidebar />
      <main className="ml-64 pt-14 min-h-screen">
        <div className="max-w-7xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-white mb-6">Понравившиеся</h1>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-[#4f46e5] border-t-transparent rounded-full animate-spin" />
            </div>
          ) : videos.length === 0 ? (
            <p className="text-gray-400">Список пуст</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
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
