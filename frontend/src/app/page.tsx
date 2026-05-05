'use client';

import { useEffect, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI } from '@/services/api';

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
  status?: string;
  category?: string;
  classification?: string;
}

const CLASSIFICATION_FILTERS = [
  { value: 'all', label: 'Все', color: 'bg-gray-600' },
  { value: 'public', label: 'Публичные', color: 'bg-green-600' },
  { value: 'internal', label: 'Внутренние', color: 'bg-blue-600' },
  { value: 'confidential', label: 'Конфиденциальные', color: 'bg-yellow-600' },
  { value: 'restricted', label: 'Личные', color: 'bg-red-600' },
];

export default function Home() {
  const [videos, setVideos] = useState<Video[]>([]);
  const [filteredVideos, setFilteredVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeClassification, setActiveClassification] = useState('all');

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const data = await videosAPI.getVideos(0, 24);
        // API returns direct array, not {videos: [...]}
        setVideos(Array.isArray(data) ? data : (data.videos || []));
      } catch (err) {
        setError('Не удалось загрузить видео');
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
  }, []);

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
      
      <main className="ml-64 pt-14 min-h-screen bg-[#0f0f0f]">
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
              <p className="text-red-400">{error}</p>
            </div>
          ) : (
            <>
              <h2 className="text-white text-xl font-semibold mb-6 flex items-center gap-2">
                <span className="w-1.5 h-6 bg-gradient-to-b from-indigo-500 to-violet-600 rounded-full"></span>
                Рекомендуемые видео
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {filteredVideos.map((video) => (
                  <VideoCard key={video.id} video={video} />
                ))}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}
