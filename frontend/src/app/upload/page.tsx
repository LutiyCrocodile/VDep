'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { videosAPI, channelsAPI, authAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';

export default function UploadPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isCollapsed } = useSidebar();
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [classification, setClassification] = useState('internal');
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
  const [selectedUsers, setSelectedUsers] = useState<Array<{id: string, username: string, full_name?: string, email?: string}>>([]);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Array<{id: string, username: string, full_name?: string, email?: string}>>([]);
  const [isSearching, setIsSearching] = useState(false);

  const CLASSIFICATION_OPTIONS = [
    { value: 'internal', label: 'Только для сотрудников', description: 'Доступно всем авторизованным сотрудникам' },
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

    // Validate that personal videos have at least one user selected
    if (classification === 'restricted' && selectedUsers.length === 0) {
      setError('Для личного видео необходимо выбрать хотя бы одного пользователя');
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
        const detail = err.response.data.detail;
        // Ensure detail is always converted to string (handles Pydantic validation errors)
        errorMessage = typeof detail === 'string' ? detail : JSON.stringify(detail);
      } else if (err.response?.status === 413) {
        errorMessage = 'Файл слишком большой. Максимальный размер: 2GB.';
      } else if (err.response?.status === 403) {
        errorMessage = 'У вас нет канала или недостаточно прав. Создайте канал перед загрузкой видео.';
        setUserChannel(null);
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      // Final safety check - ensure errorMessage is always a string
      setError(typeof errorMessage === 'string' ? errorMessage : String(errorMessage));
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
    console.log('[User Search] searchUsers called with query:', query);
    if (!query || query.length < 2) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    try {
      console.log('[User Search] Calling authAPI.searchUsers...');
      const data = await authAPI.searchUsers(query);
      console.log('[User Search] Search results:', data);
      // Filter out already selected users
      const filtered = data.users?.filter((u: any) =>
        !selectedUsers.find(su => su.id === u.id)
      ) || [];
      console.log('[User Search] Filtered results:', filtered);
      setSearchResults(filtered.map((u: any) => ({
        id: u.id,
        username: u.username || u.email,
        full_name: u.full_name,
        email: u.email
      })));
    } catch (err: any) {
      console.error('[User Search] Failed to search users:', err);
      console.error('[User Search] Error details:', err.response?.data);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Load all users for personal video access
  const loadAllUsers = async () => {
    console.log('[User Search] loadAllUsers called');
    setIsSearching(true);
    try {
      console.log('[User Search] Calling authAPI.searchAllUsers...');
      const data = await authAPI.searchAllUsers();
      console.log('[User Search] All users:', data);
      // Filter out already selected users
      const filtered = data.users?.filter((u: any) =>
        !selectedUsers.find(su => su.id === u.id)
      ) || [];
      console.log('[User Search] Filtered results:', filtered);
      setSearchResults(filtered.map((u: any) => ({
        id: u.id,
        username: u.username || u.email,
        full_name: u.full_name,
        email: u.email
      })));
    } catch (err: any) {
      console.error('[User Search] Failed to load all users:', err);
      console.error('[User Search] Error details:', err.response?.data);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const addUser = (user: {id: string, username: string, full_name?: string, email?: string}) => {
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
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <main className={`pt-14 min-h-screen flex items-center justify-center transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
          <div className="text-center">
            <p className="text-dgi-text text-xl mb-4">Необходимо войти в систему</p>
            <button
              onClick={() => router.push('/login')}
              className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-3 rounded-lg font-medium transition-all"
            >
              Войти
            </button>
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
        <div className="max-w-2xl mx-auto p-6">
          <h1 className="text-3xl font-bold text-dgi-text mb-6 font-heading">Загрузка видео</h1>

          {!userChannel && !loadingChannel && (
            <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-2xl p-6 border border-dgi-primary/30 mb-6">
              <p className="text-dgi-text mb-4">Создайте канал для загрузки видео</p>
              <button
                onClick={() => router.push('/create-channel')}
                className="bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark text-white px-6 py-2 rounded-lg font-medium transition-all"
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
                dragActive ? 'border-dgi-primary bg-dgi-primary/10' : 'border-dgi-primary/30'
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
                  <p className="text-dgi-text font-medium">{file.name}</p>
                  <p className="text-dgi-muted text-sm">{formatFileSize(file.size)}</p>
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
                  <div className="w-16 h-16 bg-dgi-surface/80 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-dgi-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-dgi-text font-medium">Перетащите видео сюда</p>
                    <p className="text-dgi-muted text-sm mt-1">или нажмите для выбора файла</p>
                  </div>
                  <p className="text-dgi-muted text-xs">MP4, AVI, MOV до 10GB</p>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {typeof error === 'string' ? error : JSON.stringify(error)}
              </div>
            )}

            {/* Title */}
            <div>
              <label className="block text-sm font-medium text-dgi-text mb-2">
                Название *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="dgi-input"
                placeholder="Введите название видео"
                required
                maxLength={100}
              />
              <p className="text-dgi-muted text-xs mt-1 text-right">{title.length}/100</p>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-medium text-dgi-text mb-2">
                Описание
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={4}
                className="dgi-input resize-none"
                placeholder="Расскажите о содержании видео"
                maxLength={5000}
              />
              <p className="text-dgi-muted text-xs mt-1 text-right">{description.length}/5000</p>
            </div>

            {/* Classification */}
            <div>
              <label className="block text-sm font-medium text-dgi-text mb-2">
                Уровень доступа
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {CLASSIFICATION_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`cursor-pointer border rounded-lg p-3 transition-all ${
                      classification === option.value
                        ? 'border-dgi-primary bg-dgi-primary/20'
                        : 'border-dgi-primary/30 bg-dgi-bg/50 hover:border-dgi-primary/50'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="radio"
                        name="classification"
                        value={option.value}
                        checked={classification === option.value}
                        onChange={(e) => setClassification(e.target.value)}
                        className="mt-1 w-4 h-4 text-dgi-primary border-gray-600 focus:ring-dgi-primary"
                      />
                      <div>
                        <p className="text-dgi-text font-medium text-sm">{option.label}</p>
                        <p className="text-dgi-muted text-xs mt-0.5">{option.description}</p>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* User selection for restricted (personal) videos */}
            {classification === 'restricted' && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <label className="block text-sm font-medium text-dgi-text mb-2">
                  Выберите пользователей, которым будет доступно видео
                </label>
                
                {/* Search input */}
                <div className="relative mb-3">
                  <input
                    type="text"
                    value={userSearchQuery}
                    onChange={(e) => setUserSearchQuery(e.target.value)}
                    placeholder="Введите имя или username для поиска..."
                    className="w-full px-4 py-2 dgi-input border-red-200 focus:border-red-400 focus:ring-red-200/50"
                  />
                  {isSearching && (
                    <div className="absolute right-3 top-2.5 w-4 h-4 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
                  )}
                </div>

                {/* Show all users button */}
                <button
                  type="button"
                  onClick={loadAllUsers}
                  className="text-xs text-red-400 hover:text-red-300 mb-3"
                >
                  Показать всех пользователей
                </button>

                {/* Hint for min chars */}
                {userSearchQuery.length > 0 && userSearchQuery.length < 2 && !isSearching && (
                  <p className="text-dgi-muted text-xs mt-1">Введите минимум 2 символа для поиска</p>
                )}

                {/* Search results */}
                {searchResults.length > 0 && (
                  <div className="bg-white border border-red-200 rounded-lg mb-3 max-h-60 overflow-y-auto">
                    {searchResults.map((user) => (
                      <button
                        key={user.id}
                        onClick={() => addUser(user)}
                        className="w-full text-left px-4 py-3 hover:bg-red-50 text-dgi-text text-sm transition-colors border-b border-red-100 last:border-b-0"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-full dgi-avatar flex items-center justify-center font-medium text-sm flex-shrink-0">
                              {(user.full_name || user.username || user.email || 'U')[0]?.toUpperCase() || 'U'}
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-dgi-text truncate">{user.full_name || user.username}</p>
                              <div className="flex items-center gap-2 mt-0.5">
                                <p className="text-xs text-dgi-muted truncate">@{user.username}</p>
                                {user.email && (
                                  <>
                                    <span className="text-dgi-muted">•</span>
                                    <p className="text-xs text-dgi-muted truncate">{user.email}</p>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="flex-shrink-0 ml-2">
                            <svg className="w-5 h-5 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                            </svg>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {/* No results message */}
                {userSearchQuery.length >= 2 && searchResults.length === 0 && !isSearching && (
                  <p className="text-dgi-muted text-xs mt-1">Пользователи не найдены</p>
                )}

                {/* Selected users */}
                {selectedUsers.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-dgi-muted text-xs">Выбранные пользователи:</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedUsers.map((user) => (
                        <span
                          key={user.id}
                          className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-100 text-red-800 text-xs rounded-full border border-red-200"
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
              <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-lg p-4 border border-dgi-primary/30">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-dgi-text text-sm font-medium">
                    {uploadProgress < 30 ? 'Подготовка...' : 
                     uploadProgress < 80 ? 'Загрузка файла...' : 
                     uploadProgress < 100 ? 'Обработка...' : 'Загружено!'}
                  </span>
                  <span className="text-dgi-muted text-sm">{uploadProgress}%</span>
                </div>
                <div className="w-full h-2 bg-dgi-bg/50 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-dgi-primary to-dgi-primary-mid transition-all duration-500"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-dgi-muted text-xs mt-2">
                  {uploadProgress < 30 ? 'Инициализация загрузки...' : 
                   uploadProgress < 80 ? 'Загрузка видео на сервер...' : 
                   uploadProgress < 100 ? 'Сохранение...' : 'Загрузка завершена! Нажмите «Опубликовать» для начала обработки.'}
                </p>
              </div>
            )}

            {/* Upload complete - show publish button */}
            {uploadedVideoId && !isUploading && !isPublished && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-3">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-green-800 font-medium">Видео успешно загружено!</span>
                </div>
                <p className="text-dgi-muted text-sm mb-4">
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
                    className="px-6 py-3 border border-dgi-border text-dgi-text hover:bg-dgi-surface-hover rounded-lg transition-all"
                  >
                    Позже
                  </button>
                </div>
              </div>
            )}

            {/* Publishing in progress */}
            {isPublishing && (
              <div className="bg-dgi-surface/80 backdrop-blur-sm rounded-lg p-4 border border-dgi-primary/30">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
                  <span className="text-dgi-text">Начинаем обработку видео...</span>
                </div>
              </div>
            )}

            {/* Published successfully */}
            {isPublished && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center gap-3">
                  <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-green-800 font-medium">Обработка началась!</span>
                </div>
                <p className="text-dgi-muted text-sm mt-2">
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
                  className="flex-1 bg-gradient-to-r from-dgi-primary to-dgi-primary-mid hover:from-dgi-primary-mid hover:to-dgi-primary-dark disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-all"
                >
                  {isUploading ? 'Загрузка...' : 'Загрузить'}
                </button>
                <button
                  type="button"
                  onClick={() => router.push('/')}
                  disabled={isUploading}
                  className="px-6 py-3 border border-dgi-border text-dgi-text hover:bg-dgi-surface-hover rounded-lg transition-all disabled:opacity-50"
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
