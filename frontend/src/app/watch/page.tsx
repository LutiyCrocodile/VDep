'use client';

import { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import VideoCard from '@/components/video/VideoCard';
import { videosAPI, channelsAPI } from '@/services/api';
import Link from 'next/link';
import Hls from 'hls.js';
import { useSidebar } from '@/contexts/SidebarContext';

interface Video {
  id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  duration?: number;
  views_count?: number;
  created_at: string;
  user_id?: string;
  owner_username?: string;
  channel_id?: string;
  channel_handle?: string;
  channel_name?: string;
  status?: string;
  hls_playlist_url?: string;
  hls_url?: string;
  qualities?: { quality: string; url: string }[];
}

export default function WatchPage() {
  const searchParams = useSearchParams();
  const videoId = searchParams.get('v');
  const { isCollapsed } = useSidebar();
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const [video, setVideo] = useState<Video | null>(null);
  const [relatedVideos, setRelatedVideos] = useState<Video[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [volume, setVolume] = useState(1);
  const [showControls, setShowControls] = useState(true);
  const [currentQuality, setCurrentQuality] = useState('auto');
  const [showQualityMenu, setShowQualityMenu] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [playlistUrl, setPlaylistUrl] = useState<string>('');
  const [likesCount, setLikesCount] = useState(0);
  const [userLiked, setUserLiked] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [showShareToast, setShowShareToast] = useState(false);
  const [availableQualities, setAvailableQualities] = useState<{level: number, name: string}[]>([]);
  const [isSeeking, setIsSeeking] = useState(false);
  const [playerReady, setPlayerReady] = useState(false);
  const [isVideoLoading, setIsVideoLoading] = useState(false);
  const [mouseActive, setMouseActive] = useState(true);
  const hlsRef = useRef<Hls | null>(null);
  const progressRef = useRef<HTMLDivElement>(null);
  const inactivityTimerRef = useRef<NodeJS.Timeout | null>(null);
  const viewRecordedRef = useRef(false);

  // Reset player state when video changes
  useEffect(() => {
    setIsPlaying(false);
    setIsVideoLoading(false);
    setCurrentTime(0);
    setVideoDuration(0);
    setPlayerReady(false);
    setMouseActive(true);
    setAvailableQualities([]);
    viewRecordedRef.current = false; // Reset view flag for new video
    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
  }, [videoId]);

  // Record view when video starts playing
  const recordVideoView = async () => {
    if (!videoId || viewRecordedRef.current) return;

    try {
      const response = await videosAPI.recordView(videoId);
      viewRecordedRef.current = true;
      // Increment views count locally only if it's a new view
      if (!response.already_viewed) {
        setVideo(prev => prev ? { ...prev, views_count: (prev.views_count || 0) + 1 } : null);
        console.log('New view recorded for video:', videoId);
      } else {
        console.log('View already recorded for this user');
      }
    } catch (err) {
      console.error('Failed to record view:', err);
    }
  };

  // Handle mouse inactivity
  const handleMouseActivity = () => {
    setMouseActive(true);
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }
    inactivityTimerRef.current = setTimeout(() => {
      if (isPlaying) {
        setMouseActive(false);
      }
    }, 1000);
  };

  // Clear timer on unmount
  useEffect(() => {
    return () => {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    };
  }, []);

  // Fetch signed playlist URL
  useEffect(() => {
    const fetchPlaylist = async () => {
      if (!videoId) return;
      try {
        const url = await videosAPI.getPlaylist(videoId);
        setPlaylistUrl(url);
      } catch (err) {
        console.log('Playlist not ready yet');
      }
    };
    fetchPlaylist();
  }, [videoId, video?.status]);

  // Initialize HLS and handle play
  const handlePlay = async () => {
    if (!playlistUrl) return;
    
    const videoElement = videoRef.current;
    if (!videoElement) return;

    // If already playing, just toggle
    if (playerReady && isPlaying) {
      videoElement.pause();
      setIsPlaying(false);
      return;
    }

    // If already loaded but paused, play
    if (playerReady && !isPlaying) {
      videoElement.play().then(() => {
        setIsPlaying(true);
        recordVideoView(); // Record view when user starts watching
      }).catch(() => {});
      return;
    }

    // Start loading
    setIsVideoLoading(true);
    console.log('Starting video load...');

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        debug: true,
        startLevel: 0, // Start with lowest quality
      });
      hlsRef.current = hls;

      hls.on(Hls.Events.MEDIA_ATTACHED, () => {
        console.log('HLS attached, loading source...');
        hls.loadSource(playlistUrl);
      });

      hls.on(Hls.Events.MANIFEST_PARSED, (event, data) => {
        console.log('Manifest parsed, levels:', data.levels.length);
        setAvailableQualities(data.levels.map((l, i) => ({
          level: i,
          name: l.height ? `${l.height}p` : `Level ${i + 1}`
        })));
        
        if (data.levels.length > 0 && data.levels[0].details) {
          setVideoDuration(data.levels[0].details.totalduration);
        }
        
        // Start loading video
        hls.startLoad(0);
      });

      hls.on(Hls.Events.BUFFER_CREATED, () => {
        console.log('Buffer created');
      });

      // Check for buffered data
      const checkBuffered = () => {
        if (videoElement.buffered.length > 0) {
          const bufferedEnd = videoElement.buffered.end(0);
          console.log('Buffered:', bufferedEnd);
          if (bufferedEnd > 0.5) {
            setIsVideoLoading(false);
            setPlayerReady(true);
            setIsPlaying(true);
            videoElement.play().then(() => {
              recordVideoView(); // Record view on first play
            }).catch(() => {});
            return true;
          }
        }
        return false;
      };

      // Poll for buffer
      let attempts = 0;
      const pollBuffer = () => {
        if (checkBuffered()) return;
        attempts++;
        if (attempts < 100) {
          setTimeout(pollBuffer, 200);
        } else {
          setIsVideoLoading(false);
          console.error('Buffer timeout');
        }
      };

      hls.on(Hls.Events.FRAG_BUFFERED, () => {
        console.log('Fragment buffered');
        checkBuffered();
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('HLS error:', data);
        if (data.fatal) {
          setIsVideoLoading(false);
        }
      });

      hls.attachMedia(videoElement);
      
      // Start polling after a short delay
      setTimeout(pollBuffer, 500);

    } else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS
      videoElement.src = playlistUrl;
      videoElement.addEventListener('loadedmetadata', () => {
        setVideoDuration(videoElement.duration);
        setIsVideoLoading(false);
        setPlayerReady(true);
        setIsPlaying(true);
        videoElement.play().then(() => {
          recordVideoView(); // Record view for Safari
        }).catch(() => {});
      });
      videoElement.addEventListener('error', () => {
        setIsVideoLoading(false);
        console.error('Video load error');
      });
    }
  };


  // Fullscreen toggle
  const toggleFullscreen = () => {
    const container = videoRef.current?.parentElement;
    if (!container) return;
    
    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  // Volume control
  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (videoRef.current) {
      videoRef.current.volume = newVolume;
    }
  };

  // Quality control
  const handleQualityChange = (quality: string) => {
    setCurrentQuality(quality);
    if (!hlsRef.current) return;
    
    if (quality === 'auto') {
      hlsRef.current.currentLevel = -1; // Auto
    } else {
      // Find level index by quality name (e.g., "720p")
      const qualityNum = parseInt(quality);
      const levelIndex = availableQualities.findIndex(q => q.name === quality);
      if (levelIndex !== -1) {
        hlsRef.current.currentLevel = availableQualities[levelIndex].level;
      }
    }
  };

  // Seek control
  const handleSeek = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressRef.current || !videoRef.current || !videoDuration) return;
    
    const rect = progressRef.current.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    const newTime = pos * videoDuration;
    
    videoRef.current.currentTime = newTime;
    setCurrentTime(newTime);
  };

  // Handle progress bar interaction
  const handleProgressMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    setIsSeeking(true);
    handleSeek(e);
  };

  const handleProgressMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isSeeking) {
      handleSeek(e);
    }
  };

  const handleProgressMouseUp = () => {
    setIsSeeking(false);
  };

  // Like handlers
  const handleLike = async () => {
    if (!videoId) return;
    try {
      if (userLiked) {
        await videosAPI.unlikeVideo(videoId);
        setUserLiked(false);
        setLikesCount(prev => prev - 1);
      } else {
        await videosAPI.likeVideo(videoId);
        setUserLiked(true);
        setLikesCount(prev => prev + 1);
      }
    } catch (err) {
      console.error('Like error:', err);
    }
  };

  // Subscribe handler
  const handleSubscribe = async () => {
    if (!video?.channel_id) return;
    try {
      if (isSubscribed) {
        await channelsAPI.unsubscribe(video.channel_id);
        setIsSubscribed(false);
      } else {
        await channelsAPI.subscribe(video.channel_id);
        setIsSubscribed(true);
      }
    } catch (err) {
      console.error('Subscribe error:', err);
    }
  };

  // Share handler
  const handleShare = () => {
    if (!videoId) return;
    const link = videosAPI.getShareLink(videoId);
    navigator.clipboard.writeText(link).then(() => {
      setShowShareToast(true);
      setTimeout(() => setShowShareToast(false), 3000);
    });
  };

  useEffect(() => {
    const fetchVideo = async () => {
      if (!videoId) return;
      
      try {
        const data = await videosAPI.getVideo(videoId);
        console.log('Video data received:', data);
        console.log('Views count:', data.views_count, typeof data.views_count);
        setVideo(data);

        // Fetch likes
        const likesData = await videosAPI.getVideoLikes(videoId);
        setLikesCount(likesData.likes_count);
        setUserLiked(likesData.user_liked);
        
        // Check subscription if channel exists
        if (data.channel_id) {
          const subData = await channelsAPI.isSubscribed(data.channel_id);
          setIsSubscribed(subData.is_subscribed);
        }
      } catch (err) {
        setError('Видео не найдено');
        // Mock data
        setVideo({
          id: videoId,
          title: 'Демо видео - Обзор системы',
          description: 'Это демонстрационное видео для тестирования интерфейса.',
          views_count: 1500,
          created_at: new Date().toISOString(),
          owner_username: 'Администратор',
          duration: 600,
          status: 'ready',
          hls_url: '',
        });
      } finally {
        setIsLoading(false);
      }
    };

    const fetchRelated = async () => {
      try {
        const data = await videosAPI.getVideos(0, 10);
        setRelatedVideos((data.videos || []).filter((v: Video) => v.id !== videoId).slice(0, 8));
      } catch {
        setRelatedVideos([
          {
            id: '2',
            title: 'Совещание отдела имущества - 2024',
            views_count: 890,
            created_at: new Date(Date.now() - 86400000).toISOString(),
            owner_username: 'Менеджер',
            duration: 3600,
            status: 'ready',
          },
          {
            id: '3',
            title: 'Инструкция по работе с системой',
            views_count: 2100,
            created_at: new Date(Date.now() - 172800000).toISOString(),
            owner_username: 'HR',
            duration: 900,
            status: 'ready',
          },
        ]);
      }
    };

    fetchVideo();
    fetchRelated();
  }, [videoId]);

  const formatDuration = (seconds?: number) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const roundedSeconds = Math.floor(seconds);
    const mins = Math.floor(roundedSeconds / 60);
    const secs = roundedSeconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatViews = (count: number | undefined | null) => {
    const num = Number(count) || 0;
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0a0a1a]">
        <Header />
        <div className="flex items-center justify-center h-screen">
          <div className="w-10 h-10 border-3 border-indigo-500 border-t-transparent rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !video) {
    return (
      <div className="min-h-screen bg-[#0a0a1a]">
        <Header />
        <div className="flex flex-col items-center justify-center h-screen">
          <p className="text-white text-xl">{error || 'Видео не найдено'}</p>
          <Link href="/" className="mt-4 text-indigo-400 hover:text-indigo-300 transition-colors">
            Вернуться на главную
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0a1a]">
      <Header />
      <Sidebar />
      
      <main className={`pt-14 min-h-screen bg-[#0a0a1a] transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'}`}>
        <div className="flex gap-6 p-6">
          {/* Main content */}
          <div className="flex-1 max-w-5xl">
            {/* Video Player */}
            <div 
              className="relative aspect-video bg-black rounded-2xl overflow-hidden group border border-[#27274a] shadow-2xl shadow-indigo-500/10"
              onMouseMove={handleMouseActivity}
              onMouseEnter={handleMouseActivity}
              onClick={() => {
                if (playlistUrl) {
                  // If already playing, pause. Otherwise play/start loading
                  if (isPlaying && playerReady) {
                    const videoElement = videoRef.current;
                    if (videoElement) {
                      videoElement.pause();
                      setIsPlaying(false);
                    }
                  } else {
                    handlePlay();
                  }
                }
              }}
            >
              <video
                ref={videoRef}
                className={`w-full h-full ${playerReady ? 'opacity-100' : 'opacity-0'}`}
                poster={video.thumbnail_url || `https://via.placeholder.com/1280x720/1a1a3e/FFFFFF?text=${encodeURIComponent(video.title)}`}
                onClick={() => {
                  // Direct pause/play on video click
                  const videoElement = videoRef.current;
                  if (!videoElement) return;
                  
                  if (isPlaying) {
                    videoElement.pause();
                    setIsPlaying(false);
                  } else {
                    handlePlay();
                  }
                }}
                onTimeUpdate={(e) => {
                  if (!isSeeking) {
                    setCurrentTime(e.currentTarget.currentTime);
                  }
                }}
                onLoadedMetadata={(e) => {
                  setVideoDuration(e.currentTarget.duration);
                }}
                onDurationChange={(e) => {
                  setVideoDuration(e.currentTarget.duration);
                }}
                onEnded={() => {
                  setIsPlaying(false);
                }}
                playsInline
              />
              
              {/* Center loading spinner - показываем пока идет загрузка */}
              {isVideoLoading && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                  <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
              )}

              {/* Play button overlay - показываем когда можно нажать play */}
              {!isPlaying && playlistUrl && !playerReady && !isVideoLoading && (
                <div 
                  className="absolute inset-0 flex items-center justify-center z-20 cursor-pointer"
                  onClick={handlePlay}
                >
                  <button 
                    onClick={(e) => { e.stopPropagation(); handlePlay(); }}
                    className="w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 shadow-lg bg-gradient-to-br from-indigo-500 to-violet-600 hover:from-indigo-400 hover:to-violet-500 hover:shadow-indigo-500/60 hover:scale-110 shadow-indigo-500/40"
                  >
                    <svg className="w-12 h-12 ml-1 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Pause overlay - показываем когда видео на паузе и загружено, полупрозрачная кнопка */}
              {!isPlaying && playerReady && !isVideoLoading && (
                <div 
                  className={`absolute inset-0 flex items-center justify-center z-20 cursor-pointer transition-opacity duration-300 ${mouseActive ? 'opacity-100' : 'opacity-0'}`}
                  onClick={handlePlay}
                >
                  <button 
                    onClick={(e) => { e.stopPropagation(); handlePlay(); }}
                    className="w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 bg-indigo-500/60 hover:bg-indigo-500/80 hover:scale-110"
                  >
                    <svg className="w-12 h-12 ml-1 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Controls overlay - с анимацией скрытия вниз */}
              <div className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t from-[#0a0a1a] via-[#0a0a1a]/80 to-transparent p-6 z-30 transition-transform duration-300 ease-out ${mouseActive || !isPlaying ? 'translate-y-0' : 'translate-y-full'}`}>
                {/* Progress bar - неактивна пока грузится */}
                <div 
                  ref={progressRef}
                  className={`w-full h-1.5 bg-[#27274a] rounded-full mb-4 ${playerReady ? 'cursor-pointer group/progress' : 'cursor-not-allowed'}`}
                  onMouseDown={playerReady ? handleProgressMouseDown : undefined}
                  onMouseMove={playerReady ? handleProgressMouseMove : undefined}
                  onMouseUp={playerReady ? handleProgressMouseUp : undefined}
                  onMouseLeave={playerReady ? handleProgressMouseUp : undefined}
                >
                  <div 
                    className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full relative"
                    style={{ width: `${(currentTime / (videoDuration || 1)) * 100}%` }}
                  >
                    <div className={`absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-white rounded-full transition-opacity ${playerReady ? 'opacity-0 group-hover/progress:opacity-100' : 'opacity-0'}`} />
                  </div>
                </div>
                
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={handlePlay}
                      disabled={!playlistUrl || isVideoLoading}
                      className="hover:bg-white/10 rounded-full p-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {isPlaying ? (
                        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                        </svg>
                      ) : (
                        <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                        </svg>
                      )}
                    </button>
                    <span className="text-white text-sm font-medium">{formatDuration(currentTime)} / {formatDuration(videoDuration)}</span>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    {/* Quality selector */}
                    <div className="relative">
                      <button 
                        onClick={() => setShowQualityMenu(!showQualityMenu)}
                        className="px-3 py-1 bg-[#1a1a3e]/80 hover:bg-[#252550] text-white text-sm rounded-lg transition-colors border border-[#27274a]"
                      >
                        {currentQuality === 'auto' ? 'Авто' : currentQuality}
                      </button>
                      {showQualityMenu && (
                        <div className="absolute bottom-full right-0 mb-2 bg-[#1a1a3e] border border-[#27274a] rounded-xl overflow-hidden shadow-xl min-w-[120px]">
                          <button
                            onClick={() => { handleQualityChange('auto'); setShowQualityMenu(false); }}
                            className={`w-full px-4 py-2 text-sm text-left transition-colors ${
                              currentQuality === 'auto'
                                ? 'bg-gradient-to-r from-indigo-600/30 to-violet-600/30 text-white'
                                : 'text-zinc-400 hover:bg-[#252550] hover:text-white'
                            }`}
                          >
                            Авто
                          </button>
                          {availableQualities.map((quality) => (
                            <button
                              key={quality.level}
                              onClick={() => { handleQualityChange(quality.name); setShowQualityMenu(false); }}
                              className={`w-full px-4 py-2 text-sm text-left transition-colors ${
                                currentQuality === quality.name
                                  ? 'bg-gradient-to-r from-indigo-600/30 to-violet-600/30 text-white'
                                  : 'text-zinc-400 hover:bg-[#252550] hover:text-white'
                              }`}
                            >
                              {quality.name}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    {/* Volume */}
                    <div className="flex items-center gap-2">
                      <svg className="w-5 h-5 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                      </svg>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={volume}
                        onChange={handleVolumeChange}
                        className="w-20 h-1 bg-[#27274a] rounded-full appearance-none cursor-pointer accent-indigo-500"
                      />
                    </div>
                    
                    {/* Fullscreen */}
                    <button 
                      onClick={toggleFullscreen}
                      className="hover:bg-white/10 rounded-full p-2 transition-colors"
                    >
                      <svg className="w-5 h-5 text-zinc-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Video info */}
            <div className="mt-6">
              <h1 className="text-2xl font-bold text-white">{video.title}</h1>
              
              <div className="flex items-center justify-between mt-4">
                <div className="flex items-center gap-4">
                  <Link
                    href={video.channel_handle ? `/channel/${video.channel_handle}` : (video.owner_username ? `/channel/${video.owner_username}` : '#')}
                    className="w-12 h-12 rounded-full bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/40 transition-all"
                  >
                    {video.owner_username?.[0]?.toUpperCase() || 'U'}
                  </Link>
                  <div>
                    <Link
                      href={video.channel_handle ? `/channel/${video.channel_handle}` : (video.owner_username ? `/channel/${video.owner_username}` : '#')}
                      className="text-white font-semibold hover:text-indigo-400 transition-colors block"
                    >
                      {video.owner_username || 'Неизвестный'}
                    </Link>
                    <p className="text-zinc-400 text-sm">{formatViews(video.views_count)} просмотров • {formatDate(video.created_at)}</p>
                  </div>
                  {video.channel_id && (
                    <button
                      onClick={handleSubscribe}
                      className={`ml-4 px-6 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 shadow-lg ${
                        isSubscribed
                          ? 'bg-zinc-700 text-white hover:bg-zinc-600'
                          : 'bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-indigo-500/20 hover:shadow-indigo-500/40'
                      }`}
                    >
                      {isSubscribed ? 'Подписан' : 'Подписаться'}
                    </button>
                  )}
                </div>
                
                <div className="flex items-center gap-3">
                  <button 
                    onClick={handleLike}
                    className={`flex items-center gap-2 px-5 py-2.5 rounded-full transition-all duration-200 border ${
                      userLiked
                        ? 'bg-gradient-to-r from-indigo-600 to-violet-600 border-transparent text-white'
                        : 'bg-[#1a1a3e] hover:bg-[#252550] text-white border-[#27274a] hover:border-indigo-500/30'
                    }`}
                  >
                    <svg className={`w-5 h-5 ${userLiked ? 'text-white' : 'text-indigo-400'}`} fill="currentColor" viewBox="0 0 20 20">
                      <path d="M2 10.5a1.5 1.5 0 113 0v6a1.5 1.5 0 01-3 0v-6zM6 10.333v5.43a2 2 0 001.106 1.79l.05.025A4 4 0 008.943 18h5.416a2 2 0 001.962-1.608l1.2-6A2 2 0 0015.56 8H12V4a2 2 0 00-2-2 1 1 0 00-1 1v.667a4 4 0 01-.8 2.4L6.8 7.933a4 4 0 00-.8 2.4z" />
                    </svg>
                    <span className="font-medium">{userLiked ? 'Нравится' : 'Нравится'} {likesCount > 0 && `(${formatViews(likesCount)})`}</span>
                  </button>
                  <button 
                    onClick={handleShare}
                    className="flex items-center gap-2 bg-[#1a1a3e] hover:bg-[#252550] text-white px-5 py-2.5 rounded-full transition-all duration-200 border border-[#27274a] hover:border-indigo-500/30"
                  >
                    <svg className="w-5 h-5 text-violet-400" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M15 8a3 3 0 10-2.977-2.63l-4.94 2.47a3 3 0 100 4.319l4.94 2.47a3 3 0 10.895-1.789l-4.94-2.47a3.027 3.027 0 000-.74l4.94-2.47C13.456 7.68 14.19 8 15 8z" />
                    </svg>
                    <span className="font-medium">Поделиться</span>
                  </button>
                </div>
              </div>

              {/* Description */}
              <div className="mt-4 bg-[#1a1a3e] border border-[#27274a] rounded-xl p-5">
                <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{video.description || 'Описание отсутствует'}</p>
              </div>
            </div>
          </div>

          {/* Related videos */}
          <div className="w-96 flex-shrink-0">
            <h3 className="text-white font-semibold mb-4 text-lg">Похожие видео</h3>
            <div className="space-y-4">
              {relatedVideos.map((v) => (
                <Link key={v.id} href={`/watch?v=${v.id}`} className="flex gap-3 group">
                  <div className="relative w-40 aspect-video rounded-xl overflow-hidden bg-[#1a1a3e] border border-[#27274a] flex-shrink-0 group-hover:border-indigo-500/30 transition-all duration-200">
                    <img 
                      src={v.thumbnail_url || `https://via.placeholder.com/160x90/1a1a3e/FFFFFF?text=${encodeURIComponent(v.title.substring(0, 15))}`}
                      alt={v.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    {v.duration && (
                      <div className="absolute bottom-1.5 right-1.5 bg-[#0a0a1a]/90 text-white text-xs px-1.5 py-0.5 rounded font-medium">
                        {formatDuration(v.duration)}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-white text-sm font-medium line-clamp-2 group-hover:text-indigo-400 transition-colors duration-200">
                      {v.title}
                    </h4>
                    <p className="text-zinc-400 text-xs mt-1">{v.owner_username}</p>
                    <p className="text-zinc-500 text-xs">{formatViews(v.views_count)} просмотров</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </main>
      
      {/* Share Toast */}
      {showShareToast && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-[#1a1a3e] border border-[#27274a] text-white px-6 py-3 rounded-xl shadow-xl z-50 animate-fade-in">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span>Ссылка скопирована!</span>
          </div>
        </div>
      )}
    </div>
  );
}
