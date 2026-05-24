'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';

export default function HistoryPage() {
  const { user } = useAuth();
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { isCollapsed } = useSidebar();

  useEffect(() => {
    const fetchHistory = async () => {
      if (user) {
        try {
          const data = await videosAPI.getViewHistory();
          setVideos(data.history || []);
        } catch (err) {
          console.error('Failed to fetch history:', err);
        } finally {
          setLoading(false);
        }
      }
    };
    fetchHistory();
  }, [user]);

  if (!user) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <main className={`pt-14 min-h-screen flex items-center justify-center transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <p className="text-dgi-text">Войдите для просмотра истории</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen dgi-gradient-bg">
      <Header />
      <Sidebar />
      <main className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="max-w-7xl mx-auto p-6">
          <h1 className="dgi-page-title">История просмотров</h1>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="w-8 h-8 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
            </div>
          ) : videos.length === 0 ? (
            <p className="text-dgi-muted">История пуста</p>
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
