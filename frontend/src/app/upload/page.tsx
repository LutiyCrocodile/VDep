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
  const [classification, setClassification] = useState('public');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const [loadingChannel, setLoadingChannel] = useState(true);
  const [uploadedVideoId, setUploadedVideoId] = useState<string | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isPublished, setIsPublished] = useState(false);
  
  // For restricted (personal) videos - user access management
  const [selectedUsers, setSelectedUsers] = useState<Array<{id: string, username: string, full_name?: string}>>([]);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{id: string, username: string, full_name?: string}>>([]);
  const [isSearching, setIsSearching] = useState(false);

  const CLASSIFICATION_OPTIONS = [
    { value: 'public', label: 'Публичный', description: 'Видео доступно всем пользователям' },
    { value: 'internal', label: 'Внутренний', description: 'Доступно только зарегистрированным пользователям' },
    { value: 'confidential', label: 'Конфиденциальный', description: 'Доступно только сотрудникам ДГИ' },
    { value: 'restricted', label: 'Личный', description: 'Доступно только выбранным пользователям' },
  ];

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
      const result = await videosAPI.uploadVideo(file, { title, description, channelId: userChannel.id, classification }, (progress) => {
        setUploadProgress(progress);
      });
      
      console.log('Upload successful:', result);
      
      // Save video_id for publishing
      setUploadedVideoId(result.video_id);
      setIsUploading(false);
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

  const handlePublishVideo = async () => {
    if (!uploadedVideoId) return;
    
    // Validate that personal videos have at least one user selected
    if (classification === 'restricted' && selectedUsers.length === 0) {
      setError('Для личного видео необходимо выбрать хотя бы одного пользователя');
      return;
    }
    
    setIsPublishing(true);
    try {
      // For personal videos, first grant access to selected users
      if (classification === 'restricted' && selectedUsers.length > 0) {
        for (const user of selectedUsers) {
          await videosAPI.grantVideoAccess(uploadedVideoId, user.id);
        }
      }
      
      // Then publish the video
      await videosAPI.publishVideo(uploadedVideoId);
      setIsPublished(true);
      
      // Redirect after successful publish
      setTimeout(() => {
        router.push('/');
      }, 2000);
    } catch (err: any) {
      console.error('Publish error:', err);
      const errorMessage = err.response?.data?.detail || 'Не удалось опубликовать видео';
      setError(errorMessage);
    } finally {
      setIsPublishing(false);
    }
  };

  // Search users for personal video access
  const searchUsers = async (query: string) => {
    console.log('searchUsers called with query:', query);
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }
    
    setIsSearching(true);
    try {
      const token = localStorage.getItem('token');
      console.log('Using token:', token ? 'present' : 'missing');
      
      // Use auth service to search users
      const apiUrl = process.env.NEXT_PUBLIC_AUTH_API_URL || 'http://localhost:8000';
      const url = `${apiUrl}/api/v1/users/search?q=${encodeURIComponent(query)}`;
      console.log('Fetching from:', url);
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      
      console.log('Response status:', response.status);
      
      if (response.ok) {
        const data = await response.json();
        console.log('Search results:', data);
        // Filter out already selected users
        const filtered = data.users?.filter((u: any) => 
          !selectedUsers.find(su => su.id === u.id)
        ) || [];
        console.log('Filtered results:', filtered);
        setSearchResults(filtered.map((u: any) => ({ 
          id: u.id, 
          username: u.username || u.email,
          full_name: u.full_name 
        })));
      } else {
        const errorText = await response.text();
        console.error('Search failed:', response.status, errorText);
      }
    } catch (err) {
      console.error('Failed to search users:', err);
    } finally {
      setIsSearching(false);
    }
  };

  const addUser = (user: {id: string, username: string, full_name?: string}) => {
    if (!selectedUsers.find(u => u.id === user.id)) {
      setSelectedUsers([...selectedUsers, user]);
    }
    setUserSearchQuery('');
    setSearchResults([]);
  };

  const removeUser = (userId: string) => {
    setSelectedUsers(selectedUsers.filter(u => u.id !== userId));
  };

  // Debounced search effect
  useEffect(() => {
    if (!userSearchQuery || userSearchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const timeoutId = setTimeout(() => {
      searchUsers(userSearchQuery);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [userSearchQuery]);

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

            {/* Classification */}
            <div>
              <label className="block text-sm font-medium text-white mb-2">
                Уровень доступа
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {CLASSIFICATION_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`cursor-pointer border rounded-lg p-3 transition-all ${
                      classification === option.value
                        ? 'border-[#4f46e5] bg-[#4f46e5]/20'
                        : 'border-[#4f46e5]/30 bg-[#0a0a1a]/50 hover:border-[#4f46e5]/50'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="classification"
                        value={option.value}
                        checked={classification === option.value}
                        onChange={(e) => setClassification(e.target.value)}
                        className="mt-1 w-4 h-4 text-[#4f46e5] border-gray-600 focus:ring-[#4f46e5]"
                      />
                      <div>
                        <p className="text-white font-medium text-sm">{option.label}</p>
                        <p className="text-gray-400 text-xs mt-0.5">{option.description}</p>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* User selection for restricted (personal) videos */}
            {classification === 'restricted' && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <label className="block text-sm font-medium text-white mb-2">
                  Выберите пользователей, которым будет доступно видео
                </label>
                
                {/* Search input */}
                <div className="relative mb-3">
                  <input
                    type="text"
                    value={userSearchQuery}
                    onChange={(e) => setUserSearchQuery(e.target.value)}
                    placeholder="Введите имя или username для поиска..."
                    className="w-full px-4 py-2 bg-[#0a0a1a]/50 border border-red-500/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-red-500/50"
                  />
                  {isSearching && (
                    <div className="absolute right-3 top-2.5 w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                  )}
                </div>

                {/* Hint for min chars */}
                {userSearchQuery.length > 0 && userSearchQuery.length < 2 && !isSearching && (
                  <p className="text-gray-500 text-xs mt-1">Введите минимум 2 символа для поиска</p>
                )}

                {/* Search results */}
                {searchResults.length > 0 && (
                  <div className="bg-[#0a0a1a]/80 border border-red-500/20 rounded-lg mb-3 max-h-40 overflow-y-auto">
                    {searchResults.map((user) => (
                      <button
                        key={user.id}
                        onClick={() => addUser(user)}
                        className="w-full text-left px-3 py-2 hover:bg-red-500/20 text-white text-sm transition-colors flex items-center justify-between"
                      >
                        <div className="flex items-center gap-2">
                          <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                          </svg>
                          <div>
                            <p className="font-medium">{user.full_name || user.username}</p>
                            {user.full_name && (
                              <p className="text-xs text-gray-400">@{user.username}</p>
                            )}
                          </div>
                        </div>
                        <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </button>
                    ))}
                  </div>
                )}

                {/* No results message */}
                {userSearchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
                  <p className="text-gray-500 text-xs mt-1">Пользователи не найдены</p>
                )}

                {/* Selected users */}
                {selectedUsers.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-gray-400 text-xs">Выбранные пользователи:</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedUsers.map((user) => (
                        <span
                          key={user.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-500/30 text-red-200 text-xs rounded-full"
                          title={`@${user.username}`}
                        >
                          <span className="font-medium">{user.full_name || user.username}</span>
                          <button
                            onClick={() => removeUser(user.id)}
                            className="hover:text-red-400 ml-1"
                          >
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedUsers.length === 0 && (
                  <p className="text-red-400/70 text-xs mt-2">
                    Выберите хотя бы одного пользователя для личного видео
                  </p>
                )}
              </div>
            )}

            {/* Progress */}
            {isUploading && (
              <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-lg p-4 border border-[#4f46e5]/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white text-sm">
                    {uploadProgress < 30 ? 'Подготовка...' : 
                     uploadProgress < 80 ? 'Загрузка файла...' : 
                     uploadProgress < 100 ? 'Обработка...' : 'Загружено!'}
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
                   uploadProgress < 100 ? 'Сохранение...' : 'Загрузка завершена! Нажмите "Опубликовать" для начала обработки.'}
                </p>
              </div>
            )}

            {/* Upload complete - show publish button */}
            {uploadedVideoId && !isUploading && !isPublished && (
              <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-white font-medium">Видео успешно загружено!</span>
                </div>
                <p className="text-gray-400 text-sm mb-4">
                  Видео сохранено на сервере. Нажмите кнопку ниже, чтобы начать обработку и опубликовать видео.
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={handlePublishVideo}
                    disabled={isPublishing}
                    className="flex-1 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 disabled:opacity-50 text-white font-medium py-3 px-4 rounded-lg transition-all flex items-center justify-center gap-2"
                  >
                    {isPublishing ? (
                      <>
                        <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Публикация...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        Опубликовать
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => router.push('/')}
                    className="px-6 py-3 border border-gray-600 text-gray-300 hover:bg-gray-800 rounded-lg transition-all"
                  >
                    Позже
                  </button>
                </div>
              </div>
            )}

            {/* Publishing in progress */}
            {isPublishing && (
              <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-lg p-4 border border-[#4f46e5]/30">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  <span className="text-white">Начинаем обработку видео...</span>
                </div>
              </div>
            )}

            {/* Published successfully */}
            {isPublished && (
              <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-white font-medium">Обработка началась!</span>
                </div>
                <p className="text-gray-400 text-sm mt-2">
                  Видео поставлено в очередь на обработку. Перенаправляем на главную страницу...
                </p>
              </div>
            )}

            {/* Submit buttons - only show before upload */}
            {!uploadedVideoId && !isPublished && (
              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={!file || !title || isUploading}
                  className="flex-1 bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] hover:from-[#4338ca] hover:to-[#6d28d9] disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-all"
                >
                  {isUploading ? 'Загрузка...' : 'Загрузить'}
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
            )}
          </form>
        </div>
      </main>
    </div>
  );
}
