'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI, channelsAPI, authAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';
import { useSidebar } from '@/contexts/SidebarContext';

type Visibility = 'dgi_employees' | 'private';

type SelectedUser = { id: string; username: string; full_name?: string; email?: string };

type ArchivingSession = {
  stream_id: string;
  title: string;
  phase: string;
  progress: number;
  error?: string | null;
  video_id?: string | null;
};

function archivePhaseLabel(phase: string): string {
  switch (phase) {
    case 'pending':
      return 'Запуск сохранения записи…';
    case 'waiting_recording':
      return 'Ожидание файла записи…';
    case 'uploading':
      return 'Загрузка на канал…';
    case 'transcoding':
      return 'Кодирование видео (HLS)…';
    case 'failed':
      return 'Ошибка сохранения';
    default:
      return 'Сохранение записи…';
  }
}

const RTMP_HOST = process.env.NEXT_PUBLIC_RTMP_HOST || 'localhost';
const RTMP_PORT = process.env.NEXT_PUBLIC_RTMP_PORT || '1935';
const RTMP_APP = process.env.NEXT_PUBLIC_RTMP_APP || 'live';

const POLL_MS = 2000;

export default function GoLivePage() {
  const router = useRouter();
  const { user } = useAuth();
  const { isCollapsed } = useSidebar();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState<Visibility>('dgi_employees');
  const [saveRecording, setSaveRecording] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const [loadingChannel, setLoadingChannel] = useState(true);
  const [currentStream, setCurrentStream] = useState<any>(null);
  const [loadingStream, setLoadingStream] = useState(true);
  const [rtmpState, setRtmpState] = useState<string | null>(null);
  const [archivingSessions, setArchivingSessions] = useState<ArchivingSession[]>([]);
  const [streamEndedNotice, setStreamEndedNotice] = useState(false);

  const [selectedUsers, setSelectedUsers] = useState<SelectedUser[]>([]);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SelectedUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const loadMyStream = useCallback(async () => {
    try {
      const data = await streamsAPI.getMyActiveStream();
      const nextRtmp = data?.rtmp_state ?? null;
      const nextStream = data?.stream ?? null;
      const nextArchiving = (data?.archiving || []).map((a: ArchivingSession) => ({
        stream_id: a.stream_id,
        title: a.title,
        phase: a.phase,
        progress: a.progress ?? 0,
        error: a.error,
        video_id: a.video_id,
      }));

      setRtmpState((prev) => {
        if ((prev === 'live' || prev === 'waiting_obs') && !nextStream && nextRtmp === null) {
          setStreamEndedNotice(true);
        }
        return nextRtmp;
      });
      setCurrentStream(nextStream);
      setArchivingSessions(nextArchiving);
    } catch (err: unknown) {
      console.error('getMyActiveStream', err);
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Не удалось загрузить состояние трансляции');
    } finally {
      setLoadingStream(false);
    }
  }, []);

  useEffect(() => {
    if (user) {
      fetchUserChannel();
      loadMyStream();
    }
  }, [user, loadMyStream]);

  useEffect(() => {
    if (!user) return;
    const interval = setInterval(loadMyStream, POLL_MS);
    return () => clearInterval(interval);
  }, [user, loadMyStream]);

  useEffect(() => {
    if (!streamEndedNotice) return;
    const t = setTimeout(() => setStreamEndedNotice(false), 8000);
    return () => clearTimeout(t);
  }, [streamEndedNotice]);

  const fetchUserChannel = async () => {
    try {
      const channel = await channelsAPI.getUserChannel();
      setUserChannel(channel);
    } catch (err: any) {
      if (err.response?.status !== 404) {
        console.error('Error fetching channel:', err);
      }
    } finally {
      setLoadingChannel(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => {
      if (!userSearchQuery || userSearchQuery.length < 2) {
        setSearchResults([]);
        return;
      }
      (async () => {
        setIsSearching(true);
        try {
          const data = await authAPI.searchUsers(userSearchQuery);
          const filtered =
            data.users?.filter((u: any) => !selectedUsers.find((su) => su.id === u.id)) || [];
          setSearchResults(
            filtered.map((u: any) => ({
              id: u.id,
              username: u.username || u.email,
              full_name: u.full_name,
              email: u.email,
            }))
          );
        } catch {
          setSearchResults([]);
        } finally {
          setIsSearching(false);
        }
      })();
    }, 350);
    return () => clearTimeout(t);
  }, [userSearchQuery, selectedUsers]);

  const addUser = (u: SelectedUser) => {
    if (!selectedUsers.find((x) => x.id === u.id)) {
      setSelectedUsers([...selectedUsers, u]);
    }
    setUserSearchQuery('');
    setSearchResults([]);
  };

  const removeUser = (id: string) => {
    setSelectedUsers(selectedUsers.filter((u) => u.id !== id));
  };

  const handleCreateStream = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;

    if (!userChannel) {
      setError('Сначала создайте канал для запуска трансляции');
      return;
    }

    if (visibility === 'private' && selectedUsers.length === 0) {
      setError('Для приватной трансляции выберите хотя бы одного зрителя');
      return;
    }

    setIsCreating(true);
    setError('');
    setStreamEndedNotice(false);
    try {
      const stream = await streamsAPI.createStream({
        title,
        description,
        visibility,
        allowed_user_ids: visibility === 'private' ? selectedUsers.map((u) => u.id) : [],
        save_recording: saveRecording,
      });
      setCurrentStream(stream);
      setRtmpState('waiting_obs');
      setTitle('');
      setDescription('');
      setSelectedUsers([]);
      await loadMyStream();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || '';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(errorMessage || 'Ошибка создания трансляции');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCancelPrepared = async () => {
    if (!currentStream) return;
    try {
      await streamsAPI.cancelPreparedStream(currentStream.id);
      setCurrentStream(null);
      setRtmpState(null);
      setError('');
      await loadMyStream();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Не удалось отменить подготовку');
    }
  };

  const handleDismissArchive = async (streamId: string) => {
    try {
      await streamsAPI.dismissArchive(streamId);
      await loadMyStream();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Не удалось сбросить');
    }
  };

  const handleRetryArchive = async (streamId: string) => {
    try {
      setError('');
      await streamsAPI.retryArchive(streamId);
      await loadMyStream();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Не удалось повторить сохранение');
    }
  };

  const isSessionLive = rtmpState === 'live' || !!currentStream?.is_live;
  const showRtmpSession =
    !!currentStream && (rtmpState === 'waiting_obs' || rtmpState === 'live' || isSessionLive);

  const rtmpServerUrl = currentStream?.rtmp_server_url || `rtmp://${RTMP_HOST}:${RTMP_PORT}/${RTMP_APP}`;
  const streamKey = currentStream?.rtmp_stream_key || currentStream?.rtmp_key || '';
  const fullRtmp = `${rtmpServerUrl}/${streamKey}`;

  if (!user) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <Sidebar />
        <main
          className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'} p-8`}
        >
          <div className="text-dgi-text text-center py-20">
            <h1 className="text-3xl font-bold mb-4 font-heading">Войдите для запуска трансляции</h1>
            <button onClick={() => router.push('/login')} className="px-6 py-3 dgi-btn-primary rounded-lg">
              Войти
            </button>
          </div>
        </main>
      </div>
    );
  }

  if (loadingChannel || loadingStream) {
    return (
      <div className="min-h-screen dgi-gradient-bg">
        <Header />
        <Sidebar />
        <main
          className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'} p-8`}
        >
          <div className="text-dgi-muted text-center py-20">Загрузка...</div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen dgi-gradient-bg">
      <Header />
      <Sidebar />
      <main
        className={`pt-14 min-h-screen transition-all duration-300 ease-in-out ${isCollapsed ? 'ml-0' : 'ml-64'} p-8`}
      >
        <div className="max-w-4xl mx-auto space-y-8">
          <h1 className="text-4xl font-bold text-dgi-text mb-2 font-heading">Запустить трансляцию</h1>
          <p className="text-dgi-muted text-sm mb-6">
            Создайте трансляцию, подключите OBS по RTMP и завершите эфир в OBS. Запись прошлых эфиров
            сохраняется на канал в фоне — можно начать новый эфир, не дожидаясь загрузки.
          </p>

          {streamEndedNotice && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-green-800 text-sm font-medium">
                Трансляция завершена (OBS отключён). Можно создать новую трансляцию.
              </p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          )}

          {!userChannel && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <p className="text-red-700 mb-4">У вас нет канала. Создайте канал перед запуском трансляции.</p>
              <button
                onClick={() => router.push('/create-channel')}
                className="px-4 py-2 dgi-btn-primary text-white rounded-lg transition"
              >
                Создать канал
              </button>
            </div>
          )}

          {archivingSessions.length > 0 && (
            <div className="space-y-4">
              {archivingSessions.map((item) => (
                <div key={item.stream_id} className="dgi-card p-6 border-l-4 border-l-amber-500">
                  <h2 className="text-lg font-semibold text-dgi-text mb-1 font-heading">
                    Сохранение записи (фон)
                  </h2>
                  <p className="text-dgi-text mb-3">{item.title}</p>
                  {item.phase === 'failed' ? (
                    <>
                      <p className="text-red-700 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2 mb-3">
                        {item.error || 'Не удалось сохранить запись'}
                      </p>
                      <div className="flex flex-wrap gap-3">
                        <button
                          type="button"
                          onClick={() => handleRetryArchive(item.stream_id)}
                          className="px-4 py-2 dgi-btn-primary rounded-lg text-sm"
                        >
                          Повторить
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDismissArchive(item.stream_id)}
                          className="px-4 py-2 border border-dgi-border rounded-lg text-dgi-text text-sm hover:bg-white"
                        >
                          Скрыть
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex items-center justify-between gap-4 mb-3">
                        <span className="text-dgi-text text-sm font-medium">
                          {archivePhaseLabel(item.phase)}
                        </span>
                        <div className="w-5 h-5 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin flex-shrink-0" />
                      </div>
                      <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-1">
                        <div
                          className="h-full bg-gradient-to-r from-dgi-primary to-dgi-primary-mid transition-all duration-500"
                          style={{ width: `${Math.max(item.progress, 8)}%` }}
                        />
                      </div>
                      <p className="text-dgi-muted text-xs">{item.progress}%</p>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {showRtmpSession ? (
            <div className="dgi-card p-6">
              <h2 className="text-2xl font-bold text-dgi-text mb-4 font-heading">Текущая трансляция</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-dgi-muted mb-2 text-sm">Название</label>
                  <p className="text-dgi-text text-lg">{currentStream.title}</p>
                </div>
                {currentStream.description && (
                  <div>
                    <label className="block text-dgi-muted mb-2 text-sm">Описание</label>
                    <p className="text-dgi-text">{currentStream.description}</p>
                  </div>
                )}
                <div>
                  <label className="block text-dgi-muted mb-2 text-sm">RTMP сервер</label>
                  <div className="flex gap-2">
                    <input type="text" value={rtmpServerUrl} readOnly className="dgi-input flex-1 text-sm font-mono" />
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(rtmpServerUrl)}
                      className="px-4 py-2 dgi-btn-primary text-white rounded transition"
                    >
                      Копировать
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-dgi-muted mb-2 text-sm">Ключ потока</label>
                  <div className="flex gap-2">
                    <input type="text" value={streamKey} readOnly className="dgi-input flex-1 font-mono text-sm" />
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(streamKey)}
                      className="px-4 py-2 dgi-btn-primary text-white rounded transition"
                    >
                      Копировать
                    </button>
                  </div>
                </div>
                <div className="bg-dgi-surface-hover rounded-lg p-4 border border-dgi-border">
                  <p className="text-dgi-muted mb-2 text-sm">Полный RTMP URL:</p>
                  <code className="text-dgi-primary text-sm break-all">{fullRtmp}</code>
                </div>
                {currentStream.save_recording === false && (
                  <p className="rounded-lg px-4 py-3 text-sm border bg-amber-50 border-amber-200 text-amber-900">
                    Запись на канал после эфира не сохраняется.
                  </p>
                )}
                <p
                  className={`rounded-lg px-4 py-3 text-sm border font-medium ${
                    isSessionLive
                      ? 'bg-green-50 border-green-200 text-green-900'
                      : 'bg-sky-50 border-sky-200 text-sky-900'
                  }`}
                >
                  {isSessionLive
                    ? 'В эфире (RTMP подключён)'
                    : 'Ожидание OBS — нажмите «Начать трансляцию» в OBS'}
                </p>
                {isSessionLive && (
                  <p className="rounded-lg px-4 py-3 text-sm border bg-dgi-surface-hover border-dgi-border text-dgi-text">
                    Чтобы завершить эфир, остановите вывод в OBS. Страница обновится автоматически после
                    отключения RTMP.
                  </p>
                )}
                <div className="flex flex-wrap gap-4">
                  {isSessionLive && (
                    <button
                      type="button"
                      onClick={() => router.push(`/stream/${currentStream.id}`)}
                      className="px-6 py-3 dgi-btn-primary rounded-lg"
                    >
                      Страница просмотра (HLS)
                    </button>
                  )}
                  {rtmpState === 'waiting_obs' && !isSessionLive && (
                    <button
                      type="button"
                      onClick={handleCancelPrepared}
                      className="px-6 py-3 border border-dgi-border rounded-lg text-dgi-text hover:bg-white transition"
                    >
                      Отменить подготовку
                    </button>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreateStream} className="space-y-6 dgi-card p-6">
              <h2 className="text-xl font-semibold text-dgi-text font-heading">Новая трансляция</h2>
              <div>
                <label className="block text-dgi-muted mb-2 text-sm">Название трансляции *</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="dgi-input"
                  placeholder="Введите название трансляции"
                  required
                />
              </div>
              <div>
                <label className="block text-dgi-muted mb-2 text-sm">Описание</label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="dgi-input"
                  placeholder="Описание (необязательно)"
                  rows={4}
                />
              </div>
              <div className="border border-dgi-border rounded-lg p-4 bg-dgi-surface-hover">
                <label className="flex items-start gap-3 text-dgi-text cursor-pointer">
                  <input
                    type="checkbox"
                    checked={saveRecording}
                    onChange={(e) => setSaveRecording(e.target.checked)}
                    className="mt-1 accent-dgi-primary"
                  />
                  <span>
                    <span className="font-medium block">Сохранить запись на канал после эфира</span>
                    <span className="text-dgi-muted text-sm">
                      Если снять галочку, после завершения трансляции видео на канал не попадёт — только
                      прямой эфир.
                    </span>
                  </span>
                </label>
              </div>
              <div>
                <label className="block text-dgi-muted mb-2 text-sm">Кто может смотреть</label>
                <div className="space-y-2">
                  <label className="flex items-center gap-2 text-dgi-text cursor-pointer">
                    <input
                      type="radio"
                      name="vis"
                      checked={visibility === 'dgi_employees'}
                      onChange={() => setVisibility('dgi_employees')}
                      className="accent-dgi-primary"
                    />
                    Только сотрудники ДГИ
                  </label>
                  <label className="flex items-center gap-2 text-dgi-text cursor-pointer">
                    <input
                      type="radio"
                      name="vis"
                      checked={visibility === 'private'}
                      onChange={() => setVisibility('private')}
                      className="accent-dgi-primary"
                    />
                    Приватная — выбранные пользователи
                  </label>
                </div>
              </div>
              {visibility === 'private' && (
                <div className="border border-dgi-border rounded-lg p-4 bg-dgi-surface-hover">
                  <label className="block text-dgi-muted mb-2 text-sm">Зрители (мин. 2 символа)</label>
                  <input
                    type="text"
                    value={userSearchQuery}
                    onChange={(e) => setUserSearchQuery(e.target.value)}
                    placeholder="Поиск..."
                    className="dgi-input mb-2"
                  />
                  {isSearching && <p className="text-dgi-muted text-sm">Поиск...</p>}
                  {searchResults.length > 0 && (
                    <ul className="max-h-40 overflow-y-auto border border-dgi-border rounded mb-3">
                      {searchResults.map((u) => (
                        <li key={u.id}>
                          <button
                            type="button"
                            onClick={() => addUser(u)}
                            className="w-full text-left px-3 py-2 text-sm text-dgi-text hover:bg-dgi-primary/10"
                          >
                            {u.username} {u.full_name ? `— ${u.full_name}` : ''}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  <div className="flex flex-wrap gap-2">
                    {selectedUsers.map((u) => (
                      <span
                        key={u.id}
                        className="inline-flex items-center gap-1 bg-dgi-primary/10 text-dgi-text text-sm px-2 py-1 rounded border border-dgi-primary/20"
                      >
                        {u.username}
                        <button type="button" onClick={() => removeUser(u.id)}>
                          ×
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <button
                type="submit"
                disabled={isCreating || !userChannel}
                className="w-full px-6 py-3 dgi-btn-primary text-white rounded-lg transition disabled:opacity-50"
              >
                {isCreating ? 'Создание...' : 'Создать трансляцию'}
              </button>
            </form>
          )}
        </div>
      </main>
    </div>
  );
}
