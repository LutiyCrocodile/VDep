'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

export default function ChannelPage() {
  const { user } = useAuth();
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
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <main className="ml-64 pt-14 min-h-screen flex items-center justify-center">
          <p className="text-white">Войдите для просмотра канала</p>
        </main>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <Sidebar />
        <main className="ml-64 pt-14 min-h-screen">
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-[#4f46e5] border-t-transparent rounded-full animate-spin" />
          </div>
        </main>
      </div>
    );
  }

  if (!channel) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <Sidebar />
        <main className="ml-64 pt-14 min-h-screen">
          <div className="max-w-4xl mx-auto p-6">
            <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-2xl p-8 border border-[#4f46e5]/30 text-center">
              <h1 className="text-2xl font-bold text-white mb-4">У вас нет канала</h1>
              <p className="text-gray-400 mb-6">Создайте канал, чтобы загружать видео</p>
              <a
                href="/create-channel"
                className="bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-3 rounded-lg font-medium transition-all"
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
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
      <Header />
      <Sidebar />
      <main className="ml-64 pt-14 min-h-screen">
        <div className="max-w-7xl mx-auto p-6">
          <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-2xl p-6 border border-[#4f46e5]/30 mb-6">
            <div className="flex items-center gap-4">
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-4xl flex-shrink-0 shadow-lg shadow-indigo-500/20">
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
