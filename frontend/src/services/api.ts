import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const VIDEO_API_URL = process.env.NEXT_PUBLIC_VIDEO_API_URL || 'http://localhost:8000/api/video';
const STREAMING_API_URL = process.env.NEXT_PUBLIC_STREAMING_API_URL || 'http://localhost:8000/api/streaming';

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
  
  uploadVideo: async (file: File, metadata: { title: string; description?: string; channelId?: string }, onProgress?: (progress: number) => void) => {
    try {
      // Step 1: Initialize upload
      const initFormData = new FormData();
      initFormData.append('title', metadata.title);
      initFormData.append('description', metadata.description || '');
      initFormData.append('filename', file.name);
      initFormData.append('file_size', file.size.toString());
      initFormData.append('is_private', 'false');
      initFormData.append('tags', '[]');
      
      console.log('[Upload] Step 1: Initializing upload...', metadata.title);
      
      const initResponse = await videoApiClient.post('/videos/upload/init', initFormData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 30000,
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
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 600000, // 10 minutes for large files
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
  
  getVideoUrl: (videoId: string) => {
    return `${VIDEO_API_URL}/videos/${videoId}/playlist.m3u8`;
  },
};

// Streams API
export const streamsAPI = {
  getStreams: async (skip = 0, limit = 20) => {
    const response = await streamingApiClient.get(`/streams?skip=${skip}&limit=${limit}`);
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

  createStream: async (data: { title: string; description?: string; is_private?: boolean }) => {
    const response = await streamingApiClient.post('/streams', data);
    return response.data;
  },

  startStream: async (streamId: string) => {
    const response = await streamingApiClient.put(`/streams/${streamId}/start`);
    return response.data;
  },
  
  stopStream: async (streamId: string) => {
    const response = await streamingApiClient.put(`/streams/${streamId}/stop`);
    return response.data;
  },

  getStreamUrl: (streamId: string) => {
    return `${STREAMING_API_URL}/hls/${streamId}/index.m3u8`;
  },
};

// Search API
export const searchAPI = {
  search: async (query: string, filters?: { tags?: string[]; date_from?: string; date_to?: string }) => {
    const params = new URLSearchParams();
    params.append('q', query);
    if (filters?.tags) {
      filters.tags.forEach(tag => params.append('tags', tag));
    }
    if (filters?.date_from) params.append('date_from', filters.date_from);
    if (filters?.date_to) params.append('date_to', filters.date_to);
    
    const response = await apiClient.get(`/search?${params.toString()}`);
    return response.data;
  },
  
  getSubtitles: async (videoId: string) => {
    const response = await apiClient.get(`/search/subtitles/${videoId}`);
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
  getNotifications: async () => {
    const response = await apiClient.get('/notifications');
    return response.data;
  },
  
  getUnreadCount: async () => {
    const response = await apiClient.get('/notifications/unread-count');
    return response.data;
  },
  
  markAsRead: async (notificationId: string) => {
    const response = await apiClient.put(`/notifications/${notificationId}/read`);
    return response.data;
  },
  
  markAllAsRead: async () => {
    const response = await apiClient.put('/notifications/read-all');
    return response.data;
  },
};

export default apiClient;
