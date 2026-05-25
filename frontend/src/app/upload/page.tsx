'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { videosAPI, channelsAPI, authAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';
import { resolveMediaUrl, withMediaCacheBust } from '@/lib/media-url';

const uploadDraftKey = (userId: string) => `dgi_upload_draft_${userId}`;

type SavedFileInfo = {
  name: string;
  size: number;
  type: string;
};

type UploadDraft = {
  videoId: string;
  title: string;
  description: string;
  classification: string;
  selectedUsers: Array<{ id: string; username: string; full_name?: string; email?: string }>;
  fileName: string;
  fileSize: number;
  fileType: string;
};

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
  const [savedFileInfo, setSavedFileInfo] = useState<SavedFileInfo | null>(null);
  const [isPublishing, setIsPublishing] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [isPublished, setIsPublished] = useState(false);
  const [pendingThumbnail, setPendingThumbnail] = useState<File | null>(null);
  const [thumbnailPreview, setThumbnailPreview] = useState<string | null>(null);
  const [hasServerThumbnail, setHasServerThumbnail] = useState(false);
  const [isThumbnailBusy, setIsThumbnailBusy] = useState(false);
  const [thumbnailRevision, setThumbnailRevision] = useState(0);
  const thumbnailInputRef = useRef<HTMLInputElement>(null);

  const selectedFileDisplay: SavedFileInfo | null = file
    ? { name: file.name, size: file.size, type: file.type }
    : savedFileInfo;
  
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

    if (uploadedVideoId) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type.startsWith('video/')) {
        setFile(droppedFile);
        setSavedFileInfo({ name: droppedFile.name, size: droppedFile.size, type: droppedFile.type });
        setTitle(droppedFile.name.replace(/\.[^/.]+$/, ''));
      }
    }
  }, [uploadedVideoId]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (uploadedVideoId) return;

    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setSavedFileInfo({ name: selectedFile.name, size: selectedFile.size, type: selectedFile.type });
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

  const fileMetaForDraft = (): Pick<UploadDraft, 'fileName' | 'fileSize' | 'fileType'> | null => {
    const info = file
      ? { name: file.name, size: file.size, type: file.type }
      : savedFileInfo;
    if (!info) return null;
    return { fileName: info.name, fileSize: info.size, fileType: info.type };
  };

  const saveUploadDraft = (videoId: string) => {
    if (!user?.id) return;
    const fileMeta = fileMetaForDraft();
    const draft: UploadDraft = {
      videoId,
      title,
      description,
      classification,
      selectedUsers,
      fileName: fileMeta?.fileName ?? title,
      fileSize: fileMeta?.fileSize ?? 0,
      fileType: fileMeta?.fileType ?? 'video/mp4',
    };
    sessionStorage.setItem(uploadDraftKey(user.id), JSON.stringify(draft));
  };

  const clearUploadDraft = () => {
    if (!user?.id) return;
    sessionStorage.removeItem(uploadDraftKey(user.id));
  };

  const clearThumbnailState = () => {
    if (thumbnailPreview?.startsWith('blob:')) {
      URL.revokeObjectURL(thumbnailPreview);
    }
    setPendingThumbnail(null);
    setThumbnailPreview(null);
    setHasServerThumbnail(false);
    setThumbnailRevision(0);
  };

  const resetPendingUpload = () => {
    clearUploadDraft();
    setUploadedVideoId(null);
    setSavedFileInfo(null);
    setFile(null);
    setUploadProgress(0);
    setIsPublished(false);
    clearThumbnailState();
  };

  useEffect(() => {
    return () => {
      if (thumbnailPreview?.startsWith('blob:')) {
        URL.revokeObjectURL(thumbnailPreview);
      }
    };
  }, [thumbnailPreview]);

  const setThumbnailPreviewFromFile = (imageFile: File) => {
    setThumbnailPreview((current) => {
      if (current?.startsWith('blob:')) {
        URL.revokeObjectURL(current);
      }
      return URL.createObjectURL(imageFile);
    });
    setPendingThumbnail(imageFile);
    setThumbnailRevision((r) => r + 1);
  };

  const applyServerThumbnailPreview = (thumbnailUrl: string) => {
    setThumbnailPreview((current) => {
      if (current?.startsWith('blob:')) {
        URL.revokeObjectURL(current);
      }
      return withMediaCacheBust(thumbnailUrl, Date.now());
    });
    setThumbnailRevision((r) => r + 1);
  };

  const uploadThumbnailToServer = async (videoId: string, imageFile: File) => {
    setIsThumbnailBusy(true);
    try {
      const result = await videosAPI.uploadVideoThumbnail(videoId, imageFile);
      setHasServerThumbnail(true);
      setPendingThumbnail(null);
      if (result.thumbnail_url) {
        applyServerThumbnailPreview(result.thumbnail_url);
      }
    } finally {
      setIsThumbnailBusy(false);
    }
  };

  const handleThumbnailChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const imageFile = e.target.files?.[0];
    e.target.value = '';
    if (!imageFile) return;

    if (!imageFile.type.startsWith('image/')) {
      setError('Для превью выберите изображение (JPEG, PNG или WebP)');
      return;
    }
    if (imageFile.size > 5 * 1024 * 1024) {
      setError('Максимальный размер превью: 5 МБ');
      return;
    }

    setError('');
    setThumbnailPreviewFromFile(imageFile);

    if (uploadedVideoId) {
      try {
        await uploadThumbnailToServer(uploadedVideoId, imageFile);
      } catch (err: any) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Не удалось загрузить превью');
        clearThumbnailState();
      }
    }
  };

  const handleRemoveThumbnail = async () => {
    setError('');
    if (uploadedVideoId && hasServerThumbnail) {
      setIsThumbnailBusy(true);
      try {
        await videosAPI.deleteVideoThumbnail(uploadedVideoId);
      } catch (err: any) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === 'string' ? detail : 'Не удалось удалить превью');
        return;
      } finally {
        setIsThumbnailBusy(false);
      }
    }
    clearThumbnailState();
  };

  useEffect(() => {
    if (!user?.id) return;

    const raw = sessionStorage.getItem(uploadDraftKey(user.id));
    if (!raw) return;

    let draft: UploadDraft;
    try {
      draft = JSON.parse(raw) as UploadDraft;
    } catch {
      clearUploadDraft();
      return;
    }

    videosAPI
      .getVideo(draft.videoId)
      .then((video) => {
        if (video.status !== 'uploaded') {
          clearUploadDraft();
          return;
        }
        setUploadedVideoId(draft.videoId);
        setTitle(draft.title);
        setDescription(draft.description);
        setClassification(draft.classification);
        setSelectedUsers(draft.selectedUsers ?? []);
        if (draft.fileName) {
          setSavedFileInfo({
            name: draft.fileName,
            size: draft.fileSize ?? 0,
            type: draft.fileType ?? 'video/mp4',
          });
        }
        if (video.thumbnail_url) {
          setHasServerThumbnail(true);
          const url = resolveMediaUrl(video.thumbnail_url, draft.videoId);
          if (url) {
            setThumbnailRevision(1);
            setThumbnailPreview(withMediaCacheBust(url, 1));
          }
        }
      })
      .catch(() => clearUploadDraft());
  }, [user?.id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !title) return;
    if (uploadedVideoId) return;

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
      
      setUploadedVideoId(result.video_id);
      if (file) {
        setSavedFileInfo({ name: file.name, size: file.size, type: file.type });
      }
      saveUploadDraft(result.video_id);
      if (pendingThumbnail) {
        try {
          await uploadThumbnailToServer(result.video_id, pendingThumbnail);
        } catch (thumbErr: any) {
          const detail = thumbErr.response?.data?.detail;
          setError(
            typeof detail === 'string'
              ? detail
              : 'Видео загружено, но не удалось сохранить превью. Попробуйте выбрать его снова.'
          );
        }
      }
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
      clearUploadDraft();
      setSavedFileInfo(null);
      setFile(null);
      clearThumbnailState();
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

  const handleCancelPublication = async () => {
    if (!uploadedVideoId) return;
    if (
      !window.confirm(
        'Удалить видео с сервера и отменить публикацию на канал? Форму можно будет заполнить заново.'
      )
    ) {
      return;
    }

    setIsCancelling(true);
    setError('');
    try {
      await videosAPI.deleteVideo(uploadedVideoId);
      resetPendingUpload();
    } catch (err: any) {
      console.error('Cancel upload error:', err);
      const errorMessage = err.response?.data?.detail || 'Не удалось отменить загрузку';
      setError(typeof errorMessage === 'string' ? errorMessage : String(errorMessage));
    } finally {
      setIsCancelling(false);
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
                dragActive && !uploadedVideoId ? 'border-dgi-primary bg-dgi-primary/10' : 'border-dgi-primary/30'
              } ${uploadedVideoId ? 'bg-dgi-primary/5' : ''}`}
            >
              <input
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                disabled={!!uploadedVideoId}
                className={`absolute inset-0 w-full h-full opacity-0 ${
                  uploadedVideoId ? 'cursor-default pointer-events-none' : 'cursor-pointer'
                }`}
              />

              {selectedFileDisplay ? (
                <div className="space-y-2">
                  <svg className="w-12 h-12 mx-auto text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-dgi-text font-medium">{selectedFileDisplay.name}</p>
                  <p className="text-dgi-muted text-sm">{formatFileSize(selectedFileDisplay.size)}</p>
                  {uploadedVideoId && (
                    <p className="text-dgi-muted text-xs">Файл загружен на сервер</p>
                  )}
                  {!uploadedVideoId && (
                    <button
                      type="button"
                      onClick={() => {
                        setFile(null);
                        setSavedFileInfo(null);
                      }}
                      className="text-red-400 hover:text-red-300 text-sm"
                    >
                      Удалить
                    </button>
                  )}
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

            {/* Custom thumbnail */}
            <div>
              <label className="block text-sm font-medium text-dgi-text mb-2">
                Превью видео
              </label>
              <p className="text-dgi-muted text-xs mb-3">
                Необязательно. Если не выбрать изображение, превью создастся автоматически при
                публикации.
              </p>
              <div className="border border-dgi-primary/30 rounded-xl p-4 bg-dgi-bg/30">
                <input
                  ref={thumbnailInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={handleThumbnailChange}
                  disabled={isThumbnailBusy || isPublishing}
                />
                {thumbnailPreview ? (
                  <div className="space-y-3">
                    <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-black shadow-inner ring-1 ring-dgi-border/60">
                      <img
                        key={thumbnailRevision}
                        src={thumbnailPreview}
                        alt="Превью видео"
                        className="absolute inset-0 w-full h-full object-cover"
                      />
                      {isThumbnailBusy && (
                        <div className="absolute inset-0 bg-black/50 flex items-center justify-center z-10">
                          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        </div>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-3 justify-center">
                      <button
                        type="button"
                        onClick={() => thumbnailInputRef.current?.click()}
                        disabled={isThumbnailBusy || isPublishing}
                        className="px-4 py-2 text-sm border border-dgi-border rounded-lg hover:bg-dgi-surface-hover text-dgi-text disabled:opacity-50"
                      >
                        Заменить
                      </button>
                      <button
                        type="button"
                        onClick={handleRemoveThumbnail}
                        disabled={isThumbnailBusy || isPublishing}
                        className="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50"
                      >
                        Удалить
                      </button>
                    </div>
                    {uploadedVideoId && hasServerThumbnail && (
                      <p className="text-center text-dgi-muted text-xs">Превью сохранено на сервере</p>
                    )}
                    {!uploadedVideoId && pendingThumbnail && (
                      <p className="text-center text-dgi-muted text-xs">
                        Превью будет загружено вместе с видео
                      </p>
                    )}
                  </div>
                ) : (
                  <button
                    type="button"
                    onClick={() => thumbnailInputRef.current?.click()}
                    disabled={isThumbnailBusy || isPublishing}
                    className="flex flex-col items-center justify-center w-full py-8 cursor-pointer hover:bg-dgi-surface-hover/50 rounded-lg transition-colors disabled:opacity-50"
                  >
                    <svg
                      className="w-10 h-10 text-dgi-muted mb-2"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                      />
                    </svg>
                    <span className="text-dgi-text text-sm font-medium">Выбрать изображение</span>
                    <span className="text-dgi-muted text-xs mt-1">JPEG, PNG, WebP до 5 МБ</span>
                  </button>
                )}
              </div>
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
                  Видео сохранено на сервере. Нажмите «Опубликовать», чтобы начать обработку и показать
                  ролик на канале. «Позже» вернёт на главную — опубликовать можно будет снова на этой
                  странице.
                </p>
                <div className="flex flex-col gap-3">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={handlePublishVideo}
                    disabled={isPublishing || isCancelling}
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
                    type="button"
                    onClick={() => {
                      if (uploadedVideoId) saveUploadDraft(uploadedVideoId);
                      router.push('/');
                    }}
                    disabled={isCancelling}
                    className="px-6 py-3 border border-dgi-border text-dgi-text hover:bg-dgi-surface-hover rounded-lg transition-all disabled:opacity-50"
                  >
                    Позже
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleCancelPublication}
                  disabled={isPublishing || isCancelling}
                  className="w-full px-6 py-3 border border-red-300 text-red-700 hover:bg-red-50 rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {isCancelling ? (
                    <>
                      <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
                      Отмена...
                    </>
                  ) : (
                    'Отменить публикацию'
                  )}
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
