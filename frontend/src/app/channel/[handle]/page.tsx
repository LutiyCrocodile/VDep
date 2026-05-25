'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { channelsAPI, videosAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';
import Link from 'next/link';

interface Channel {
  id: string;
  name: string;
  description?: string;
  handle: string;
  avatar_url?: string;
  banner_url?: string;
  owner_id: string;
  subscribers_count: number;
  is_verified: boolean;
  created_at: string;
}

interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  duration?: number;
  views_count?: number;
  created_at: string;
  status?: string;
  transcoding_progress?: number;
  user_id?: string;
  owner_username?: string;
  channel_id?: string;
}

export default function PublicChannelPage() {
  const params = useParams();
  const handle = params.handle as string;
  const { user } = useAuth();
  const { isCollapsed } = useSidebar();
  
  const [channel, setChannel] = useState<Channel | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isOwnChannel, setIsOwnChannel] = useState(false);
  const [videoToDelete, setVideoToDelete] = useState<Video | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchChannel = async () => {
      if (!handle) return;
      
      try {
        console.log('Fetching channel by handle:', handle);
        const channelData = await channelsAPI.getChannelByHandle(handle);
        console.log('Channel data:', channelData);
        setChannel(channelData);
        
        // Check if it's user's own channel
        if (user && channelData.owner_id === user.id) {
          setIsOwnChannel(true);
        }
        
        // Check subscription status
        if (user && !isOwnChannel) {
          try {
            const subStatus = await channelsAPI.isSubscribed(channelData.id);
            setIsSubscribed(subStatus.is_subscribed);
          } catch (err) {
            console.log('Could not check subscription status');
          }
        }
        
        // Fetch channel videos
        try {
          const videosData = await channelsAPI.getChannelVideos(channelData.id);
          console.log('Channel videos:', videosData);
          // Add channel name as owner_username for each video
          const videosWithChannel = (videosData || []).map((v: Video) => ({
            ...v,
            owner_username: channelData.name
          }));
          setVideos(videosWithChannel);
        } catch (err) {
          console.log('Could not fetch videos:', err);
          setVideos([]);
        }
      } catch (err: any) {
        console.error('Error fetching channel:', err);
        setError(err.response?.data?.detail || 'Канал не найден');
      } finally {
        setLoading(false);
      }
    };

    fetchChannel();
  }, [handle, user]);

  const handleSubscribe = async () => {
    if (!user) {
      // Redirect to login
      return;
    }
    
    try {
      if (isSubscribed) {
        await channelsAPI.unsubscribe(channel!.id);
        setIsSubscribed(false);
        setChannel(prev => prev ? {...prev, subscribers_count: prev.subscribers_count - 1} : null);
      } else {
        await channelsAPI.subscribe(channel!.id);
        setIsSubscribed(true);
        setChannel(prev => prev ? {...prev, subscribers_count: prev.subscribers_count + 1} : null);
      }
    } catch (err) {
      console.error('Subscription error:', err);
    }
  };

  const handleDeleteVideo = async () => {
    if (!videoToDelete || !isOwnChannel) return;
    
    setIsDeleting(true);
    try {
      await videosAPI.deleteVideo(videoToDelete.id);
      // Remove video from list
      setVideos(prev => prev.filter(v => v.id !== videoToDelete.id));
      setVideoToDelete(null);
    } catch (err) {
      console.error('Failed to delete video:', err);
      alert('Не удалось удалить видео');
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-dgi-bg to-dgi-surface">
        <Header />
        <Sidebar />
        <main className="ml-64 pt-14 min-h-screen">
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
          </div>
        </main>
      </div>
    );
  }

  if (error || !channel) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-dgi-bg to-dgi-surface">
        <Header />
        <Sidebar />
        <main className="ml-64 pt-14 min-h-screen">
          <div className="max-w-4xl mx-auto p-6">
            <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-2xl p-8 border border-dgi-primary/30 text-center">
              <h1 className="dgi-page-heading mb-4">Канал не найден</h1>
              <p className="text-dgi-muted mb-6">Канал с именем @{handle} не существует</p>
              <Link
                href="/"
                className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-3 rounded-lg font-medium transition-all"
              >
                На главную
              </Link>
            </div>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-dgi-bg to-dgi-surface">
      <Header />
      <Sidebar />
      <main className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="max-w-7xl mx-auto">
          {/* Banner */}
          {channel.banner_url ? (
            <div className="h-48 bg-cover bg-center" style={{ backgroundImage: `url(${channel.banner_url})` }} />
          ) : (
            <div className="h-32 bg-gradient-to-r from-dgi-primary/10 to-dgi-surface-hover" />
          )}
          
          {/* Channel Info */}
          <div className="px-6 py-6">
            <div className="flex items-start gap-6 -mt-16 mb-6">
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-dgi-primary to-dgi-primary-mid flex items-center justify-center text-white font-bold text-5xl flex-shrink-0 shadow-lg shadow-[0_4px_14px_rgba(200,20,30,0.2)] border-4 border-dgi-bg">
                {channel.name[0]?.toUpperCase() || 'C'}
              </div>
              <div className="flex-1 pt-16">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-dgi-text font-heading">{channel.name}</h1>
                  {channel.is_verified && (
                    <span className="text-dgi-primary" title="Проверенный канал">✓</span>
                  )}
                </div>
                <p className="text-dgi-muted">@{channel.handle}</p>
                <p className="text-dgi-muted text-sm mt-1">
                  {channel.subscribers_count?.toLocaleString() || 0} подписчиков
                </p>
              </div>
              <div className="pt-16">
                {isOwnChannel ? (
                  <Link
                    href="/upload"
                    className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-2 rounded-lg font-medium transition-all"
                  >
                    Загрузить видео
                  </Link>
                ) : (
                  <button
                    onClick={handleSubscribe}
                    className={`px-6 py-2 rounded-lg font-medium transition-all ${
                      isSubscribed
                        ? 'bg-dgi-surface-hover text-dgi-text border border-dgi-border hover:bg-gray-200'
                        : 'bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white'
                    }`}
                  >
                    {isSubscribed ? 'Отписаться' : 'Подписаться'}
                  </button>
                )}
              </div>
            </div>
            
            {channel.description && (
              <p className="text-dgi-muted mb-6 max-w-2xl">{channel.description}</p>
            )}

            {/* Videos Section */}
            <div className="mt-8">
              <h2 className="text-xl font-bold text-dgi-text mb-4 font-heading">Видео</h2>
              {videos.length === 0 ? (
                <div className="text-center py-12 bg-dgi-surface/50 rounded-2xl">
                  <p className="text-dgi-muted">На канале пока нет видео</p>
                  {isOwnChannel && (
                    <Link
                      href="/upload"
                      className="inline-block mt-4 bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-2 rounded-lg font-medium transition-all"
                    >
                      Загрузить первое видео
                    </Link>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {videos.map((video) => (
                    <div key={video.id} className="relative group">
                      <VideoCard video={video} />
                      {isOwnChannel && (
                        <button
                          onClick={() => setVideoToDelete(video)}
                          className="absolute top-2 right-2 z-10 bg-red-600/90 hover:bg-red-700 text-white p-2 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200 shadow-lg"
                          title="Удалить видео"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      {videoToDelete && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-dgi-surface border border-dgi-primary/30 rounded-2xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-xl font-bold text-dgi-text mb-4 font-heading">Удалить видео?</h3>
            <p className="text-dgi-muted mb-6">
              Вы уверены, что хотите удалить видео &quot;{videoToDelete.title}&quot;? Это действие нельзя отменить.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setVideoToDelete(null)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-dgi-surface-hover hover:bg-gray-200 text-dgi-text border border-dgi-border transition-colors disabled:opacity-50"
              >
                Отмена
              </button>
              <button
                onClick={handleDeleteVideo}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors disabled:opacity-50 flex items-center gap-2"
              >
                {isDeleting && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {isDeleting ? 'Удаление...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
