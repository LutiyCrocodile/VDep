'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';

export default function ChannelPage() {
  const { user } = useAuth();
  const { isCollapsed } = useSidebar();
  const [channel, setChannel] = useState<any>(null);
  const [videos, setVideos] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchChannel = async () => {
      if (user) {
        try {
          console.log('Fetching user channel for user:', user.id);
          const channelData = await channelsAPI.getUserChannel();
          console.log('Channel data received:', channelData);
          setChannel(channelData);
          // Fetch channel videos
          try {
            const videosData = await channelsAPI.getChannelVideos(channelData.id);
            console.log('Channel videos:', videosData);
            setVideos(videosData || []);
          } catch (videoErr) {
            console.error('Error fetching videos:', videoErr);
            setVideos([]);
          }
        } catch (err: any) {
          console.error('Error fetching user channel:', err);
          console.error('Error response:', err.response?.data);
          setChannel(null);
        } finally {
          setLoading(false);
        }
      } else {
        setLoading(false);
      }
    };
    fetchChannel();
  }, [user]);

  if (!user) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <main className={`pt-14 min-h-screen flex items-center justify-center transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <p className="text-white">Войдите для просмотра канала</p>
        </main>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <Sidebar />
        <main className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
          </div>
        </main>
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <Sidebar />
        <main className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <div className="max-w-4xl mx-auto p-6">
            <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-2xl p-8 border border-dgi-primary/30 text-center">
              <h1 className="text-2xl font-bold text-white mb-4">У вас нет канала</h1>
              <p className="text-gray-400 mb-6">Создайте канал, чтобы загружать видео</p>
              <a
                href="/create-channel"
                className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-3 rounded-lg font-medium transition-all"
              >
                Создать канал
              </a>
            </div>
          </div>
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
          <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-2xl p-6 border border-dgi-primary/30 mb-6">
            <div className="flex items-center gap-4">
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-4xl flex-shrink-0 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)]">
                {channel.name[0]?.toUpperCase() || 'C'}
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">{channel.name}</h1>
                <p className="text-gray-400">@{channel.handle}</p>
                <p className="text-gray-400 text-sm mt-1">
                  {channel.subscribers_count?.toLocaleString() || 0} подписчиков
                </p>
              </div>
            </div>
            {channel.description && (
              <p className="text-gray-300 mt-4">{channel.description}</p>
            )}
          </div>

          <h2 className="text-xl font-bold text-white mb-4">Видео канала</h2>
          {videos.length === 0 ? (
            <p className="text-gray-400">Нет видео</p>
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
