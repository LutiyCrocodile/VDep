import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const VIDEO_API_URL = process.env.NEXT_PUBLIC_VIDEO_API_URL || 'http://localhost:8001';
const STREAMING_API_URL = process.env.NEXT_PUBLIC_STREAMING_API_URL || 'http://localhost:8002';
const NOTIFICATION_API_URL =
  process.env.NEXT_PUBLIC_NOTIFICATION_API_URL || 'http://localhost:8003';
const SEARCH_API_URL =
  process.env.NEXT_PUBLIC_SEARCH_API_URL || 'http://localhost:8004';

// Create axios instances
const apiClient: AxiosInstance = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const videoApiClient: AxiosInstance = axios.create({
  baseURL: VIDEO_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const streamingApiClient: AxiosInstance = axios.create({
  baseURL: STREAMING_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const notificationApiClient: AxiosInstance = axios.create({
  baseURL: NOTIFICATION_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

const searchApiClient: AxiosInstance = axios.create({
  baseURL: SEARCH_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Add auth interceptor to video client
videoApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

notificationApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

searchApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Add auth interceptor to streaming client
streamingApiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Request interceptor - add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('access_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    
    if (error.response?.status === 401 && !originalRequest._retry && typeof window !== 'undefined') {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) {
          throw new Error('No refresh token');
        }
        
        const response = await axios.post(`${API_URL}/refresh`, { refresh_token: refreshToken });
        const { access_token, refresh_token } = response.data;
        
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);
        
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        
        return apiClient(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await axios.post(`${API_URL}/token`, formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  
  register: async (userData: { username: string; email: string; password: string; full_name?: string }) => {
    const response = await axios.post(`${API_URL}/register`, userData);
    return response.data;
  },
  
  getProfile: async () => {
    const response = await apiClient.get('/users/me');
    return response.data;
  },
  
  getUsers: async () => {
    const response = await apiClient.get('/users');
    return response.data;
  },

  searchAllUsers: async () => {
    const response = await apiClient.get('/users/search-all');
    return response.data;
  },

  searchUsers: async (query: string) => {
    const response = await apiClient.get(`/users/search?q=${encodeURIComponent(query)}`);
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/logout');
    return response.data;
  },
};

// Videos API
export const videosAPI = {
  getVideos: async (skip = 0, limit = 20) => {
    const response = await videoApiClient.get(`/videos?skip=${skip}&limit=${limit}`);
    return response.data;
  },
  
  getVideo: async (videoId: string) => {
    const response = await videoApiClient.get(`/videos/${videoId}`);
    return response.data;
  },
  
  uploadVideo: async (file: File, metadata: { title: string; description?: string; channelId?: string; classification?: string }, onProgress?: (progress: number) => void) => {
    try {
      // Step 1: Initialize upload
      const initFormData = new FormData();
      initFormData.append('title', metadata.title);
      initFormData.append('description', metadata.description || '');
      initFormData.append('filename', file.name);
      initFormData.append('file_size', file.size.toString());
      initFormData.append('is_private', 'false');
      initFormData.append('tags', '[]');
      initFormData.append('classification', metadata.classification || 'public');
      if (metadata.channelId) {
        initFormData.append('channel_id', metadata.channelId);
      }
      
      console.log('[Upload] Step 1: Initializing upload...', metadata.title);
      
      const initResponse = await videoApiClient.post('/videos/upload/init', initFormData, {
        timeout: 30000,
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      const { video_id, minio_key } = initResponse.data;
      console.log('[Upload] Step 1 complete:', { video_id, minio_key });
      
      onProgress?.(20);
      
      // Step 2: Upload file directly to video-service (avoids CORS with MinIO)
      console.log('[Upload] Step 2: Uploading file to video-service...');
      console.log('[Upload] File size:', file.size, 'File type:', file.type);
      
      const fileFormData = new FormData();
      fileFormData.append('file', file);
      
      const uploadResponse = await videoApiClient.post(`/videos/${video_id}/upload-data`, fileFormData, {
        timeout: 600000, // 10 minutes for large files
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const progress = Math.round((progressEvent.loaded / progressEvent.total) * 60) + 20; // 20-80%
            onProgress?.(progress);
            console.log('[Upload] Progress:', progress + '%');
          }
        },
      });
      
      console.log('[Upload] Step 2 complete:', uploadResponse.data);
      onProgress?.(80);
      
      // Step 3: Complete upload
      console.log('[Upload] Step 3: Completing upload...');
      const completeResponse = await videoApiClient.post(`/videos/${video_id}/complete`);
      console.log('[Upload] Step 3 complete:', completeResponse.data);
      onProgress?.(100);
      
      return {
        video_id,
        ...completeResponse.data,
      };
    } catch (error: any) {
      console.error('[Upload] Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        config: error.config,
      });
      throw error;
    }
  },
  
  deleteVideo: async (videoId: string) => {
    const response = await videoApiClient.delete(`/videos/${videoId}`);
    return response.data;
  },

  publishVideo: async (videoId: string) => {
    const response = await videoApiClient.post(`/videos/${videoId}/publish`);
    return response.data;
  },

  // Personal video access management
  grantVideoAccess: async (videoId: string, targetUserId: string) => {
    const response = await videoApiClient.post(`/videos/${videoId}/access?target_user_id=${targetUserId}`);
    return response.data;
  },

  revokeVideoAccess: async (videoId: string, targetUserId: string) => {
    const response = await videoApiClient.delete(`/videos/${videoId}/access/${targetUserId}`);
    return response.data;
  },

  getVideoAccessList: async (videoId: string) => {
    const response = await videoApiClient.get(`/videos/${videoId}/access`);
    return response.data;
  },

  getVideoUrl: (videoId: string) => {
    return `${VIDEO_API_URL}/videos/${videoId}/playlist.m3u8`;
  },
  
  getThumbnail: async (videoId: string) => {
    const response = await videoApiClient.get(`/videos/${videoId}/thumbnail`);
    return response.data.thumbnail_url;
  },
  
  getPlaylist: async (videoId: string) => {
    const response = await videoApiClient.get(`/videos/${videoId}/playlist`);
    return response.data.playlist_url;
  },
  
  // Likes
  likeVideo: async (videoId: string) => {
    const response = await videoApiClient.post(`/videos/${videoId}/like`);
    return response.data;
  },
  
  unlikeVideo: async (videoId: string) => {
    const response = await videoApiClient.delete(`/videos/${videoId}/like`);
    return response.data;
  },
  
  getVideoLikes: async (videoId: string) => {
    const response = await videoApiClient.get(`/videos/${videoId}/likes`);
    return response.data;
  },

  getLikedVideos: async (skip = 0, limit = 20) => {
    const response = await videoApiClient.get(`/videos/liked?skip=${skip}&limit=${limit}`);
    return response.data;
  },
  
  recordView: async (videoId: string) => {
    // Get or create session ID for anonymous tracking
    let sessionId = null;
    if (typeof window !== 'undefined') {
      sessionId = localStorage.getItem('anonymous_session_id');
      if (!sessionId) {
        // Generate new session ID
        sessionId = 'anon_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('anonymous_session_id', sessionId);
      }
    }
    
    const response = await videoApiClient.post(`/videos/${videoId}/views`, {
      session_id: sessionId
    });
    return response.data;
  },

  getViewHistory: async (skip = 0, limit = 50) => {
    const response = await videoApiClient.get(`/videos/history?skip=${skip}&limit=${limit}`);
    return response.data;
  },
  
  // Share - get shareable link
  getShareLink: (videoId: string) => {
    return `${typeof window !== 'undefined' ? window.location.origin : ''}/watch?v=${videoId}`;
  },
};

// Streams API
export const streamsAPI = {
  getStreams: async (skip = 0, limit = 20) => {
    const response = await streamingApiClient.get(`/streams?skip=${skip}&limit=${limit}`);
    return response.data;
  },

  getMyActiveStream: async () => {
    const response = await streamingApiClient.get('/streams/my-active');
    return response.data;
  },

  getArchiveStatus: async (streamId: string) => {
    const response = await streamingApiClient.get(`/streams/${streamId}/archive-status`);
    return response.data;
  },

  dismissArchive: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/archive/dismiss`);
    return response.data;
  },

  retryArchive: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/archive/retry`);
    return response.data;
  },

  getLiveStreams: async () => {
    const response = await streamingApiClient.get('/streams/live');
    return response.data;
  },

  getStream: async (streamId: string) => {
    const response = await streamingApiClient.get(`/streams/${streamId}`);
    return response.data;
  },

  sendPresence: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/presence`);
    return response.data;
  },

  leavePresence: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/presence/leave`);
    return response.data;
  },

  likeStream: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/like`);
    return response.data;
  },

  unlikeStream: async (streamId: string) => {
    const response = await streamingApiClient.delete(`/streams/${streamId}/like`);
    return response.data;
  },

  createStream: async (data: {
    title: string;
    description?: string;
    visibility: 'dgi_employees' | 'private';
    allowed_user_ids?: string[];
    save_recording?: boolean;
  }) => {
    const response = await streamingApiClient.post('/streams', data);
    return response.data;
  },

  startStream: async (streamId: string) => {
    const response = await streamingApiClient.put(`/streams/${streamId}/start`);
    return response.data;
  },

  /** Эфир завершается только при отключении OBS; endpoint оставлен для совместимости. */
  stopStream: async (streamId: string) => {
    const response = await streamingApiClient.put(`/streams/${streamId}/stop`);
    return response.data;
  },

  cancelPreparedStream: async (streamId: string) => {
    const response = await streamingApiClient.post(`/streams/${streamId}/cancel`);
    return response.data;
  },

  getStreamUrl: (hlsUrlFromApi?: string) => {
    if (hlsUrlFromApi) return hlsUrlFromApi;
    const base = process.env.NEXT_PUBLIC_HLS_PUBLIC_BASE || 'http://localhost:8888';
    return `${base}`;
  },
};

// Search API (search-service :8004)
export const searchAPI = {
  search: async (
    query: string,
    filters?: { tags?: string[]; skip?: number; limit?: number }
  ): Promise<{ results: unknown[]; total: number }> => {
    const params = new URLSearchParams();
    params.append('q', query);
    if (filters?.tags) {
      filters.tags.forEach((tag) => params.append('tags', tag));
    }
    if (filters?.skip != null) params.append('skip', String(filters.skip));
    if (filters?.limit != null) params.append('limit', String(filters.limit));

    const response = await searchApiClient.get(`/search?${params.toString()}`);
    const data = response.data;
    if (Array.isArray(data)) {
      return { results: data, total: data.length };
    }
    return {
      results: data.results ?? [],
      total: data.total ?? 0,
    };
  },

  getSubtitles: async (videoId: string) => {
    const response = await searchApiClient.get(`/videos/${videoId}/subtitles`);
    return response.data;
  },
};

// Channels API
export const channelsAPI = {
  createChannel: async (data: { name: string; description?: string; handle: string; avatar_url?: string; banner_url?: string }) => {
    const response = await videoApiClient.post('/channels', data);
    return response.data;
  },
  
  getChannel: async (channelId: string) => {
    const response = await videoApiClient.get(`/channels/${channelId}`);
    return response.data;
  },
  
  getChannelByHandle: async (handle: string) => {
    const response = await videoApiClient.get(`/channels/handle/${handle}`);
    return response.data;
  },
  
  getUserChannel: async () => {
    const response = await videoApiClient.get('/channels/my');
    return response.data;
  },
  
  getChannelVideos: async (channelId: string, skip = 0, limit = 20) => {
    const response = await videoApiClient.get(`/channels/${channelId}/videos?skip=${skip}&limit=${limit}`);
    return response.data;
  },
  
  subscribe: async (channelId: string) => {
    const response = await videoApiClient.post(`/channels/${channelId}/subscribe`);
    return response.data;
  },
  
  unsubscribe: async (channelId: string) => {
    const response = await videoApiClient.delete(`/channels/${channelId}/subscribe`);
    return response.data;
  },
  
  isSubscribed: async (channelId: string) => {
    const response = await videoApiClient.get(`/channels/${channelId}/is_subscribed`);
    return response.data;
  },
  
  getSubscriptions: async (skip = 0, limit = 20) => {
    const response = await videoApiClient.get(`/subscriptions?skip=${skip}&limit=${limit}`);
    return response.data;
  },
};

// Notifications API
export const notificationsAPI = {
  getNotifications: async (skip = 0, limit = 20) => {
    const response = await notificationApiClient.get(
      `/notifications?skip=${skip}&limit=${limit}`
    );
    return response.data;
  },

  getUnreadCount: async () => {
    const response = await notificationApiClient.get('/notifications/unread-count');
    return response.data;
  },

  markAsRead: async (notificationId: string) => {
    const response = await notificationApiClient.put(`/notifications/${notificationId}/read`);
    return response.data;
  },

  markAllAsRead: async () => {
    const response = await notificationApiClient.post('/notifications/mark-all-read');
    return response.data;
  },
};

export default apiClient;
