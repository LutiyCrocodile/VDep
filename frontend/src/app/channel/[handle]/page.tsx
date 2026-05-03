'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
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
  views_count: number;
  created_at: string;
  status?: string;
}

export default function PublicChannelPage() {
  const params = useParams();
  const handle = params.handle as string;
  const { user } = useAuth();
  
  const [channel, setChannel] = useState<Channel | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isOwnChannel, setIsOwnChannel] = useState(false);

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
          setVideos(videosData || []);
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

  if (error || !channel) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <Sidebar />
        <main className="ml-64 pt-14 min-h-screen">
          <div className="max-w-4xl mx-auto p-6">
            <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-2xl p-8 border border-[#4f46e5]/30 text-center">
              <h1 className="text-2xl font-bold text-white mb-4">Канал не найден</h1>
              <p className="text-gray-400 mb-6">Канал с именем @{handle} не существует</p>
              <Link
                href="/"
                className="bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-3 rounded-lg font-medium transition-all"
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
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
      <Header />
      <Sidebar />
      <main className="ml-64 pt-14 min-h-screen">
        <div className="max-w-7xl mx-auto">
          {/* Banner */}
          {channel.banner_url ? (
            <div className="h-48 bg-cover bg-center" style={{ backgroundImage: `url(${channel.banner_url})` }} />
          ) : (
            <div className="h-32 bg-gradient-to-r from-[#1a1a3e] to-[#2a2a5e]" />
          )}
          
          {/* Channel Info */}
          <div className="px-6 py-6">
            <div className="flex items-start gap-6 -mt-16 mb-6">
              <div className="w-32 h-32 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-5xl flex-shrink-0 shadow-lg shadow-indigo-500/20 border-4 border-[#0a0a1a]">
                {channel.name[0]?.toUpperCase() || 'C'}
              </div>
              <div className="flex-1 pt-16">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-white">{channel.name}</h1>
                  {channel.is_verified && (
                    <span className="text-indigo-400" title="Проверенный канал">✓</span>
                  )}
                </div>
                <p className="text-gray-400">@{channel.handle}</p>
                <p className="text-gray-400 text-sm mt-1">
                  {channel.subscribers_count?.toLocaleString() || 0} подписчиков
                </p>
              </div>
              <div className="pt-16">
                {isOwnChannel ? (
                  <Link
                    href="/upload"
                    className="bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-2 rounded-lg font-medium transition-all"
                  >
                    Загрузить видео
                  </Link>
                ) : (
                  <button
                    onClick={handleSubscribe}
                    className={`px-6 py-2 rounded-lg font-medium transition-all ${
                      isSubscribed
                        ? 'bg-gray-600 text-white hover:bg-gray-500'
                        : 'bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white'
                    }`}
                  >
                    {isSubscribed ? 'Отписаться' : 'Подписаться'}
                  </button>
                )}
              </div>
            </div>
            
            {channel.description && (
              <p className="text-gray-300 mb-6 max-w-2xl">{channel.description}</p>
            )}

            {/* Videos Section */}
            <div className="mt-8">
              <h2 className="text-xl font-bold text-white mb-4">Видео</h2>
              {videos.length === 0 ? (
                <div className="text-center py-12 bg-[#1a1a3e]/30 rounded-2xl">
                  <p className="text-gray-400">На канале пока нет видео</p>
                  {isOwnChannel && (
                    <Link
                      href="/upload"
                      className="inline-block mt-4 bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-2 rounded-lg font-medium transition-all"
                    >
                      Загрузить первое видео
                    </Link>
                  )}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                  {videos.map((video) => (
                    <VideoCard key={video.id} video={video} />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
