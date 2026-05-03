'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { videosAPI, channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

export default function UploadPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const [loadingChannel, setLoadingChannel] = useState(true);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type.startsWith('video/')) {
        setFile(droppedFile);
        setTitle(droppedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setTitle(selectedFile.name.replace(/\.[^/.]+$/, ''));
    }
  };

  useEffect(() => {
    const fetchUserChannel = async () => {
      if (user) {
        try {
          console.log('Fetching user channel...');
          const channel = await channelsAPI.getUserChannel();
          console.log('User channel found:', channel);
          setUserChannel(channel);
        } catch (err: any) {
          // Channel doesn't exist
          console.error('Error fetching user channel:', err);
          console.error('Error response:', err.response?.data);
          setUserChannel(null);
        } finally {
          setLoadingChannel(false);
        }
      } else {
        setLoadingChannel(false);
      }
    };
    fetchUserChannel();
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title) return;

    // Check if user has channel before uploading
    if (!userChannel) {
      setError('Сначала создайте канал для загрузки видео');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setError('');
    
    try {
      setUploadProgress(10); // Starting
      
      // Upload with real progress tracking
      console.log('Starting upload process...');
      await videosAPI.uploadVideo(file, { title, description, channelId: userChannel.id }, (progress) => {
        setUploadProgress(progress);
      });
      
      console.log('Upload successful, redirecting...')
      
      // Small delay to show completion
      setTimeout(() => {
        router.push('/');
      }, 1000);
    } catch (err: any) {
      console.error('Upload error:', err);
      
      // Detailed error message for debugging
      let errorMessage = 'Ошибка загрузки видео';
      
      if (err.message === 'Network Error') {
        errorMessage = 'Ошибка сети. Проверьте подключение к интернету и доступность сервера.';
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err.response?.status === 413) {
        errorMessage = 'Файл слишком большой. Максимальный размер: 2GB.';
      } else if (err.response?.status === 403) {
        errorMessage = 'У вас нет канала или недостаточно прав. Создайте канал перед загрузкой видео.';
        setUserChannel(null);
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      setUploadProgress(0);
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <main className="ml-64 pt-14 min-h-screen flex items-center justify-center">
          <div className="text-center">
            <p className="text-white text-xl mb-4">Необходимо войти в систему</p>
            <button
              onClick={() => router.push('/login')}
              className="bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-3 rounded-lg font-medium transition-all"
            >
              Войти
            </button>
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
        <div className="max-w-2xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-white mb-6">Загрузка видео</h1>

          {!userChannel && !loadingChannel && (
            <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-2xl p-6 border border-[#4f46e5]/30 mb-6">
              <p className="text-white mb-4">Создайте канал для загрузки видео</p>
              <button
                onClick={() => router.push('/create-channel')}
                className="bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] text-white px-6 py-2 rounded-lg font-medium transition-all"
              >
                Создать канал
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* File upload area */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`relative border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
                dragActive ? 'border-[#4f46e5] bg-[#4f46e5]/10' : 'border-[#4f46e5]/30'
              }`}
            >
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              
              {file ? (
                <div className="space-y-2">
                  <svg className="w-12 h-12 mx-auto text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-white font-medium">{file.name}</p>
                  <p className="text-gray-400 text-sm">{formatFileSize(file.size)}</p>
                  <button
                    type="button"
                    onClick={() => setFile(null)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Удалить
                  </button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="w-16 h-16 bg-[#1a1a3e]/50 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-white font-medium">Перетащите видео сюда</p>
                    <p className="text-gray-400 text-sm mt-1">или нажмите для выбора файла</p>
                  </div>
                  <p className="text-gray-500 text-xs">MP4, AVI, MOV до 10GB</p>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Название *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-4 py-3 bg-[#0a0a1a]/50 border border-[#4f46e5]/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 transition-all"
                placeholder="Введите название видео"
                required
                maxLength={100}
              />
              <p className="text-gray-400 text-xs mt-1 text-right">{title.length}/100</p>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Описание
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="w-full px-4 py-3 bg-[#0a0a1a]/50 border border-[#4f46e5]/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 transition-all resize-none"
                placeholder="Расскажите о содержании видео"
                maxLength={5000}
              />
              <p className="text-gray-400 text-xs mt-1 text-right">{description.length}/5000</p>
            </div>

            {/* Progress */}
            {isUploading && (
              <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-lg p-4 border border-[#4f46e5]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white text-sm">
                    {uploadProgress < 30 ? 'Подготовка...' : 
                     uploadProgress < 80 ? 'Загрузка файла...' : 
                     uploadProgress < 100 ? 'Обработка...' : 'Готово!'}
                  </span>
                  <span className="text-gray-400 text-sm">{uploadProgress}%</span>
                </div>
                <div className="w-full h-2 bg-[#0a0a1a]/50 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] transition-all duration-500"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-gray-400 text-xs mt-2">
                  {uploadProgress < 30 ? 'Инициализация загрузки...' : 
                   uploadProgress < 80 ? 'Загрузка видео на сервер...' : 
                   uploadProgress < 100 ? 'Запуск обработки видео...' : 'Загрузка завершена!'}
                </p>
              </div>
            )}

            {/* Submit buttons */}
            <div className="flex gap-4">
              <button
                type="submit"
                disabled={!file || !title || isUploading}
                className="flex-1 bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-all"
              >
                {isUploading ? 'Загрузка...' : 'Опубликовать'}
              </button>
              <button
                type="button"
                onClick={() => router.push('/')}
                disabled={isUploading}
                className="px-6 py-3 border border-[#4f46e5]/30 text-gray-300 hover:bg-[#1a1a3e]/50 rounded-lg transition-all disabled:opacity-50"
              >
                Отмена
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
