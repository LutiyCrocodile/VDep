# Интеграция фронтенда с бекендом - Полное руководство

## 1. Архитектура взаимодействия фронтенда и бекенда

### Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   React App  │  │  API Client   │  │  WebSocket   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ HTTP/HTTPS       │ HTTP/HTTPS       │ WebSocket
          │                  │                  │
┌─────────┼──────────────────┼──────────────────┼─────────────────┐
│         ▼                  ▼                  ▼                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Nginx (Reverse Proxy)                  │  │
│  │  - SSL/TLS termination                                    │  │
│  │  - Load balancing                                         │  │
│  │  - Static files serving                                   │  │
│  │  - WebSocket proxying                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │
│  │ Auth Service │   │Video Service │   │Streaming Svc │      │
│  │   :8000      │   │   :8001      │   │   :8002      │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐      │
│  │Search Service│   │Notification  │   │  WebSocket   │      │
│  │   :8004      │   │   :8003      │   │   :8005      │      │
│  └──────────────┘   └──────────────┘   └──────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

## 2. Конфигурация API клиента

### Базовая настройка Axios

```typescript
// src/lib/api/client.ts
import axios, { AxiosError, AxiosInstance } from 'axios';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://video.dgi.ru',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor - добавляем токен
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - обработка ошибок и обновление токена
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as any;

        // 401 - токен истек, пробуем обновить
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          
          try {
            const newToken = await this.refreshToken();
            this.setToken(newToken);
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            // Не удалось обновить токен - разлогиниваем
            this.clearToken();
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private getToken(): string | null {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('access_token');
    }
    return null;
  }

  private setToken(token: string): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem('access_token', token);
    }
  }

  private clearToken(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    }
  }

  private async refreshToken(): Promise<string> {
    const refreshToken = localStorage.getItem('refresh_token');
    const response = await axios.post('/api/auth/refresh', {
      refresh_token: refreshToken,
    });
    
    const { access_token, refresh_token: newRefreshToken } = response.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('refresh_token', newRefreshToken);
    
    return access_token;
  }

  public get instance(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new ApiClient();
```

### API модули для каждого сервиса

```typescript
// src/lib/api/auth.ts
import { apiClient } from './client';

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.instance.post('/api/auth/token', 
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),

  register: (data: {
    username: string;
    email: string;
    password: string;
    role_id: string;
  }) => apiClient.instance.post('/api/auth/register', data),

  refreshToken: (refreshToken: string) =>
    apiClient.instance.post('/api/auth/refresh', { refresh_token: refreshToken }),

  getCurrentUser: () =>
    apiClient.instance.get('/api/auth/users/me'),

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  },
};
```

```typescript
// src/lib/api/video.ts
import { apiClient } from './client';

export const videoApi = {
  list: (params?: { skip?: number; limit?: number; status?: string }) =>
    apiClient.instance.get('/api/video/videos', { params }),

  get: (id: string) =>
    apiClient.instance.get(`/api/video/videos/${id}`),

  getSignedUrl: (id: string) =>
    apiClient.instance.get(`/api/video/videos/${id}/signed-url`),

  initUpload: (data: {
    title: string;
    description: string;
    filename: string;
    file_size: number;
    is_private?: boolean;
    tags?: string[];
  }) => apiClient.instance.post('/api/video/videos/upload/init', data),

  completeUpload: (id: string) =>
    apiClient.instance.post(`/api/video/videos/${id}/complete`),

  update: (id: string, data: {
    title?: string;
    description?: string;
    is_private?: boolean;
    tags?: string[];
  }) => apiClient.instance.put(`/api/video/videos/${id}`, data),

  delete: (id: string) =>
    apiClient.instance.delete(`/api/video/videos/${id}`),
};
```

```typescript
// src/lib/api/streaming.ts
import { apiClient } from './client';

export const streamingApi = {
  list: () =>
    apiClient.instance.get('/api/streaming/streams'),

  get: (id: string) =>
    apiClient.instance.get(`/api/streaming/streams/${id}`),

  create: (data: {
    title: string;
    description?: string;
    scheduled_start?: string;
  }) => apiClient.instance.post('/api/streaming/streams', data),

  start: (id: string) =>
    apiClient.instance.put(`/api/streaming/streams/${id}/start`),

  stop: (id: string) =>
    apiClient.instance.put(`/api/streaming/streams/${id}/stop`),

  getStreamKey: (id: string) =>
    apiClient.instance.get(`/api/streaming/streams/${id}/rtmp-key`),
};
```

```typescript
// src/lib/api/search.ts
import { apiClient } from './client';

export const searchApi = {
  search: (query: string, filters?: {
    tags?: string[];
    date_from?: string;
    date_to?: string;
    duration_min?: number;
    duration_max?: number;
  }) => apiClient.instance.get('/api/search/search', {
    params: { q: query, ...filters }
  }),

  getSubtitles: (videoId: string) =>
    apiClient.instance.get(`/api/search/videos/${videoId}/subtitles`),

  searchInSubtitles: (videoId: string, query: string) =>
    apiClient.instance.get(`/api/search/videos/${videoId}/subtitles/search`, {
      params: { q: query }
    }),
};
```

```typescript
// src/lib/api/notifications.ts
import { apiClient } from './client';

export const notificationsApi = {
  list: (params?: { skip?: number; limit?: number; unread_only?: boolean }) =>
    apiClient.instance.get('/api/notifications/notifications', { params }),

  markAsRead: (id: string) =>
    apiClient.instance.put(`/api/notifications/notifications/${id}/read`),

  markAllAsRead: () =>
    apiClient.instance.post('/api/notifications/notifications/mark-all-read'),

  getUnreadCount: () =>
    apiClient.instance.get('/api/notifications/notifications/unread-count'),
};
```

## 3. React Query для кэширования и управления состоянием

```typescript
// src/lib/hooks/useAuth.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { authApi } from '../api/auth';
import { useRouter } from 'next/navigation';

export function useLogin() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      authApi.login(username, password),
    onSuccess: (data) => {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
      queryClient.invalidateQueries({ queryKey: ['currentUser'] });
      router.push('/dashboard');
    },
  });
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ['currentUser'],
    queryFn: authApi.getCurrentUser,
    enabled: !!localStorage.getItem('access_token'),
    retry: false,
  });
}

export function useLogout() {
  const router = useRouter();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: authApi.logout,
    onSuccess: () => {
      queryClient.clear();
      router.push('/login');
    },
  });
}
```

```typescript
// src/lib/hooks/useVideo.ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { videoApi } from '../api/video';

export function useVideos(params?: { skip?: number; limit?: number }) {
  return useQuery({
    queryKey: ['videos', params],
    queryFn: () => videoApi.list(params),
  });
}

export function useVideo(id: string) {
  return useQuery({
    queryKey: ['video', id],
    queryFn: () => videoApi.get(id),
    enabled: !!id,
  });
}

export function useVideoUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: {
      title: string;
      description: string;
      file: File;
      tags?: string[];
      is_private?: boolean;
    }) => {
      // 1. Инициализация загрузки
      const initResponse = await videoApi.initUpload({
        title: data.title,
        description: data.description,
        filename: data.file.name,
        file_size: data.file.size,
        tags: data.tags,
        is_private: data.is_private,
      });

      const { video_id, upload_url } = initResponse.data;

      // 2. Загрузка файла частями (chunked upload)
      const CHUNK_SIZE = 5 * 1024 * 1024; // 5MB
      const totalChunks = Math.ceil(data.file.size / CHUNK_SIZE);

      for (let chunk = 0; chunk < totalChunks; chunk++) {
        const start = chunk * CHUNK_SIZE;
        const end = Math.min(start + CHUNK_SIZE, data.file.size);
        const chunkData = data.file.slice(start, end);

        await fetch(upload_url, {
          method: 'PUT',
          body: chunkData,
          headers: {
            'Content-Type': data.file.type,
            'Content-Range': `bytes ${start}-${end - 1}/${data.file.size}`,
          },
        });
      }

      // 3. Завершение загрузки
      await videoApi.completeUpload(video_id);

      return video_id;
    },
    onSuccess: (videoId) => {
      queryClient.invalidateQueries({ queryKey: ['videos'] });
      queryClient.invalidateQueries({ queryKey: ['video', videoId] });
    },
  });
}

export function useVideoSignedUrl(videoId: string) {
  return useQuery({
    queryKey: ['videoSignedUrl', videoId],
    queryFn: () => videoApi.getSignedUrl(videoId),
    enabled: !!videoId,
    staleTime: 5 * 60 * 1000, // 5 минут
  });
}
```

## 4. WebSocket для real-time уведомлений

```typescript
// src/lib/hooks/useWebSocket.ts
import { useEffect, useState, useRef } from 'react';
import { io, Socket } from 'socket.io-client';

interface Notification {
  id: string;
  type: string;
  message: string;
  created_at: string;
}

export function useWebSocket(userId: string) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (!userId) return;

    const token = localStorage.getItem('access_token');
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'wss://video.dgi.ru';

    const newSocket = io(wsUrl, {
      auth: { token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });

    newSocket.on('connect', () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    });

    newSocket.on('disconnect', () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    });

    newSocket.on('notification', (notification: Notification) => {
      setNotifications((prev) => [notification, ...prev]);
      
      // Показываем browser notification
      if (Notification.permission === 'granted') {
        new Notification('Видеохостинг ДГИ', {
          body: notification.message,
          icon: '/icon.png',
        });
      }
    });

    newSocket.on('video_progress', (data: { video_id: string; progress: number }) => {
      // Обновляем прогресс транскодирования
      setNotifications((prev) => [
        ...prev,
        {
          id: data.video_id,
          type: 'video_progress',
          message: `Транскодирование: ${data.progress}%`,
          created_at: new Date().toISOString(),
        },
      ]);
    });

    newSocket.on('stream_started', (data: { stream_id: string; title: string }) => {
      setNotifications((prev) => [
        ...prev,
        {
          id: data.stream_id,
          type: 'stream_started',
          message: `Трансляция "${data.title}" началась`,
          created_at: new Date().toISOString(),
        },
      ]);
    });

    setSocket(newSocket);

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      newSocket.disconnect();
    };
  }, [userId]);

  const markAsRead = (notificationId: string) => {
    setNotifications((prev) =>
      prev.filter((n) => n.id !== notificationId)
    );
  };

  return {
    socket,
    notifications,
    isConnected,
    markAsRead,
  };
}
```

## 5. Компонент Video Player с интеграцией

```typescript
// src/components/video/VideoPlayer.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import Hls from 'hls.js';
import { useVideoSignedUrl } from '@/lib/hooks/useVideo';
import { Loader2 } from 'lucide-react';

interface VideoPlayerProps {
  videoId: string;
  poster?: string;
  autoPlay?: boolean;
  onProgress?: (currentTime: number) => void;
}

export function VideoPlayer({ videoId, poster, autoPlay = false, onProgress }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [quality, setQuality] = useState<string>('auto');
  
  const { data: signedUrlData, isLoading: urlLoading } = useVideoSignedUrl(videoId);

  useEffect(() => {
    if (!videoRef.current || !signedUrlData?.signed_url) return;

    const video = videoRef.current;
    const hlsUrl = signedUrlData.signed_url;
    setLoading(false);

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 30,
        maxMaxBufferLength: 60,
        enableWorker: true,
      });

      hls.loadSource(hlsUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
        if (autoPlay) {
          video.play().catch((e) => console.error('Autoplay failed:', e));
        }
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
              setError('Ошибка воспроизведения видео');
              break;
          }
        }
      });

      return () => hls.destroy();
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = hlsUrl;
      if (autoPlay) {
        video.play().catch((e) => console.error('Autoplay failed:', e));
      }
    }
  }, [signedUrlData, autoPlay]);

  // Отправка прогресса просмотра
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !onProgress) return;

    const handleTimeUpdate = () => {
      onProgress(video.currentTime);
    };

    video.addEventListener('timeupdate', handleTimeUpdate);
    return () => video.removeEventListener('timeupdate', handleTimeUpdate);
  }, [onProgress]);

  if (urlLoading || loading) {
    return (
      <div className="flex items-center justify-center aspect-video bg-black rounded-lg">
        <Loader2 className="w-8 h-8 text-white animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center aspect-video bg-black rounded-lg">
        <p className="text-white">{error}</p>
      </div>
    );
  }

  return (
    <div className="relative">
      <video
        ref={videoRef}
        className="w-full aspect-video bg-black rounded-lg"
        controls
        poster={poster}
        playsInline
      />
    </div>
  );
}
```

## 6. Компонент загрузки видео с прогрессом

```typescript
// src/components/video/VideoUploadModal.tsx
'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useVideoUpload } from '@/lib/hooks/useVideo';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Loader2, Upload } from 'lucide-react';

interface VideoUploadModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function VideoUploadModal({ open, onOpenChange }: VideoUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [isPrivate, setIsPrivate] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const uploadMutation = useVideoUpload();

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type.startsWith('video/')) {
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file || !title) return;

    try {
      await uploadMutation.mutateAsync({
        title,
        description,
        file,
        tags,
        is_private: isPrivate,
      });
      onOpenChange(false);
      // Сброс формы
      setFile(null);
      setTitle('');
      setDescription('');
      setTags([]);
      setIsPrivate(false);
      setUploadProgress(0);
    } catch (error) {
      console.error('Upload failed:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Загрузить видео</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="file">Видеофайл</Label>
            <Input
              id="file"
              type="file"
              accept="video/*"
              onChange={handleFileSelect}
              disabled={uploadMutation.isPending}
            />
            {file && (
              <p className="text-sm text-gray-500 mt-1">
                {file.name} ({(file.size / (1024 * 1024)).toFixed(2)} MB)
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="title">Название</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={uploadMutation.isPending}
            />
          </div>

          <div>
            <Label htmlFor="description">Описание</Label>
            <Textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={uploadMutation.isPending}
            />
          </div>

          <div>
            <Label htmlFor="tags">Теги (через запятую)</Label>
            <Input
              id="tags"
              placeholder="совещание, отчет, 2024"
              onChange={(e) => setTags(e.target.value.split(',').map(t => t.trim()).filter(Boolean))}
              disabled={uploadMutation.isPending}
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="private"
              checked={isPrivate}
              onChange={(e) => setIsPrivate(e.target.checked)}
              disabled={uploadMutation.isPending}
            />
            <Label htmlFor="private">Приватное видео</Label>
          </div>

          {uploadMutation.isPending && (
            <div>
              <Progress value={uploadProgress} />
              <p className="text-sm text-gray-500 mt-1">Загрузка...</p>
            </div>
          )}

          <Button
            onClick={handleUpload}
            disabled={!file || !title || uploadMutation.isPending}
            className="w-full"
          >
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Загрузка...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Загрузить
              </>
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

## 7. Переменные окружения для фронтенда

```bash
# .env.local
NEXT_PUBLIC_API_URL=https://video.dgi.ru
NEXT_PUBLIC_WS_URL=wss://video.dgi.ru
NEXT_PUBLIC_APP_NAME=Видеохостинг ДГИ
NEXT_PUBLIC_MAX_UPLOAD_SIZE=10737418240  # 10GB
```

## 8. Защита маршрутов

```typescript
// src/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token');
  const { pathname } = request.nextUrl;

  // Публичные маршруты
  const publicPaths = ['/login', '/register', '/watch', '/search'];
  
  if (publicPaths.some(path => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // Защищенные маршруты
  if (!token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/dashboard/:path*', '/profile/:path*', '/admin/:path*'],
};
```

## 9. Обработка ошибок

```typescript
// src/lib/utils/errorHandler.ts
import { AxiosError } from 'axios';

export interface ApiError {
  message: string;
  status?: number;
  details?: any;
}

export function handleApiError(error: unknown): ApiError {
  if (error instanceof AxiosError) {
    return {
      message: error.response?.data?.detail || error.message || 'Произошла ошибка',
      status: error.response?.status,
      details: error.response?.data,
    };
  }

  if (error instanceof Error) {
    return {
      message: error.message,
    };
  }

  return {
    message: 'Неизвестная ошибка',
  };
}

export function getErrorMessage(error: unknown): string {
  const apiError = handleApiError(error);
  
  switch (apiError.status) {
    case 401:
      return 'Сессия истекла. Пожалуйста, войдите снова.';
    case 403:
      return 'У вас нет прав для выполнения этого действия.';
    case 404:
      return 'Ресурс не найден.';
    case 413:
      return 'Файл слишком большой.';
    case 429:
      return 'Слишком много запросов. Попробуйте позже.';
    case 500:
      return 'Ошибка сервера. Попробуйте позже.';
    default:
      return apiError.message;
  }
}
```

## 10. Типы TypeScript

```typescript
// src/types/index.ts
export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface Video {
  id: string;
  title: string;
  description?: string;
  duration?: string;
  resolution?: string;
  bitrate?: number;
  file_size: number;
  status: 'uploading' | 'uploaded' | 'transcoding' | 'ready' | 'failed';
  hls_playlist_url?: string;
  is_private: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
  user_id: string;
}

export interface Stream {
  id: string;
  title: string;
  description?: string;
  rtmp_key: string;
  hls_url?: string;
  is_live: boolean;
  start_time?: string;
  end_time?: string;
  archived_video_id?: string;
  created_at: string;
}

export interface Notification {
  id: string;
  type: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface SearchResult {
  id: string;
  title: string;
  description?: string;
  tags: string[];
  score: number;
  highlights?: {
    title?: string[];
    description?: string[];
    subtitles?: string[];
  };
}
```
