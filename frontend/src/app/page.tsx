'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI, searchAPI } from '@/services/api';
import { useSidebar } from '@/contexts/SidebarContext';

interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  duration?: number;
  views_count: number;
  created_at: string;
  user_id?: string;
  owner_username?: string;
  channel_handle?: string;
  status?: string;
  category?: string;
  classification?: string;
}

const CLASSIFICATION_FILTERS = [
  { value: 'all', label: 'Все', color: 'bg-gray-600' },
  { value: 'restricted', label: 'Личные', color: 'bg-red-600' },
];

export default function Home() {
  const searchParams = useSearchParams();
  const searchQuery = searchParams.get('q') || '';
  const [videos, setVideos] = useState<Video[]>([]);
  const [filteredVideos, setFilteredVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeClassification, setActiveClassification] = useState('all');
  const { isCollapsed } = useSidebar();

  useEffect(() => {
    const fetchVideos = async () => {
      setIsLoading(true);
      setError('');
      try {
        let data;
        if (searchQuery.trim()) {
          console.log('[Search] Using search API with query:', searchQuery);
          // Use search API for full-text search
          try {
            data = await searchAPI.search(searchQuery);
            console.log('[Search] Search API response:', data);
            setVideos(Array.isArray(data) ? data : (data.results || data.videos || []));
          } catch (searchError: any) {
            console.error('[Search] Search API failed, falling back to video API:', searchError);
            // Fallback: use video API and filter client-side
            data = await videosAPI.getVideos(0, 100);
            const allVideos = Array.isArray(data) ? data : (data.videos || []);
            const filtered = allVideos.filter((v: Video) =>
              v.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
              (v.description && v.description.toLowerCase().includes(searchQuery.toLowerCase()))
            );
            setVideos(filtered);
          }
        } else {
          console.log('[Search] Using regular videos API (no search query)');
          // Use regular videos API
          data = await videosAPI.getVideos(0, 24);
          setVideos(Array.isArray(data) ? data : (data.videos || []));
        }
      } catch (err: any) {
        console.error('[Search] Error fetching videos:', err);
        const errorDetail = err.response?.data?.detail || err.message || 'Не удалось загрузить видео';
        const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
        setError(errorMessage);
        // Mock data for demonstration with categories
        setVideos([
          {
            id: '1',
            title: 'Обзор нового проекта - ДГИ Москва',
            description: 'Видеообзор нового проекта',
            views_count: 1250,
            created_at: new Date().toISOString(),
            owner_username: 'Администратор',
            duration: 480,
            status: 'ready',
            category: 'Проекты',
          },
          {
            id: '2',
            title: 'Совещание отдела имущества - 2024',
            description: 'Еженедельное совещание',
            views_count: 890,
            created_at: new Date(Date.now() - 86400000).toISOString(),
            owner_username: 'Менеджер',
            duration: 3600,
            status: 'ready',
            category: 'Совещания',
          },
          {
            id: '3',
            title: 'Инструкция по работе с системой',
            description: 'Обучающее видео',
            views_count: 2100,
            created_at: new Date(Date.now() - 172800000).toISOString(),
            owner_username: 'HR',
            duration: 900,
            status: 'ready',
            category: 'Обучение',
          },
          {
            id: '4',
            title: 'Новости компании - Май 2024',
            description: 'Актуальные новости',
            views_count: 1500,
            created_at: new Date(Date.now() - 259200000).toISOString(),
            owner_username: 'Пресс-служба',
            duration: 600,
            status: 'ready',
            category: 'Новости',
          },
          {
            id: '5',
            title: 'Прямая трансляция: Отчет за квартал',
            description: 'Live stream',
            views_count: 3200,
            created_at: new Date().toISOString(),
            owner_username: 'Директор',
            duration: 5400,
            status: 'ready',
            category: 'Прямые трансляции',
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    fetchVideos();
  }, [searchQuery]);

  // Filter videos - only ready videos on home page, then by classification
  useEffect(() => {
    // First filter: only ready videos (exclude uploading/transcoding videos)
    let result = videos.filter(v => v.status === 'ready');
    
    // Second filter: by classification
    if (activeClassification !== 'all') {
      result = result.filter(v => v.classification === activeClassification);
    }
    
    setFilteredVideos(result);
  }, [activeClassification, videos]);

  return (
    <div className="min-h-screen bg-[#0f0f0f]">
      <Header />
      <Sidebar />
      
      <main className={`pt-14 min-h-screen bg-[#0f0f0f] transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="p-6">
          {/* Classification Filters */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2">
            {CLASSIFICATION_FILTERS.map((filter) => (
              <button
                key={filter.value}
                onClick={() => setActiveClassification(filter.value)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all flex items-center gap-2 ${
                  activeClassification === filter.value
                    ? `${filter.color} text-white shadow-lg`
                    : 'bg-[#272727] text-gray-300 hover:bg-[#3f3f3f]'
                }`}
              >
                {activeClassification === filter.value && (
                  <span className="w-2 h-2 bg-white rounded-full" />
                )}
                {filter.label}
              </button>
            ))}
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-400">{typeof error === 'string' ? error : JSON.stringify(error)}</p>
            </div>
          ) : (
            <>
              {searchQuery && (
                <h2 className="text-white text-xl font-semibold mb-6 flex items-center gap-2">
                  <span className="w-1.5 h-6 bg-gradient-to-b from-indigo-500 to-violet-600 rounded-full"></span>
                  Результаты поиска: "{searchQuery}"
                </h2>
              )}
              {filteredVideos.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-400 text-lg">
                    {searchQuery ? 'По вашему запросу ничего не найдено' : 'Нет доступных видео'}
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                  {filteredVideos.map((video) => (
                    <VideoCard key={video.id} video={video} />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
