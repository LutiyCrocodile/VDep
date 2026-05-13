'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI, channelsAPI, authAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

type Visibility = 'dgi_employees' | 'private';

type SelectedUser = { id: string; username: string; full_name?: string; email?: string };

const RTMP_HOST = process.env.NEXT_PUBLIC_RTMP_HOST || 'localhost';
const RTMP_PORT = process.env.NEXT_PUBLIC_RTMP_PORT || '1935';
const RTMP_APP = process.env.NEXT_PUBLIC_RTMP_APP || 'live';

export default function GoLivePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [visibility, setVisibility] = useState<Visibility>('dgi_employees');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const [loadingChannel, setLoadingChannel] = useState(true);
  const [currentStream, setCurrentStream] = useState<any>(null);
  const [loadingStream, setLoadingStream] = useState(true);

  const [selectedUsers, setSelectedUsers] = useState<SelectedUser[]>([]);
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SelectedUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devicesOk, setDevicesOk] = useState(false);
  const [audioInputId, setAudioInputId] = useState('');
  const [videoInputId, setVideoInputId] = useState('');
  const [micDevices, setMicDevices] = useState<MediaDeviceInfo[]>([]);
  const [camDevices, setCamDevices] = useState<MediaDeviceInfo[]>([]);

  const loadMyStream = useCallback(async () => {
    try {
      const data = await streamsAPI.getMyActiveStream();
      if (data?.stream) {
        setCurrentStream(data.stream);
      } else {
        setCurrentStream(null);
      }
    } catch (err) {
      console.error('getMyActiveStream', err);
      setCurrentStream(null);
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

  const refreshDevices = async () => {
    try {
      const list = await navigator.mediaDevices.enumerateDevices();
      setMicDevices(list.filter((d) => d.kind === 'audioinput'));
      setCamDevices(list.filter((d) => d.kind === 'videoinput'));
    } catch {
      /* ignore */
    }
  };

  const stopPreview = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setDevicesOk(false);
  };

  const startPreview = async () => {
    setError('');
    try {
      stopPreview();
      const constraints: MediaStreamConstraints = {
        audio: audioInputId ? { deviceId: { exact: audioInputId } } : true,
        video: videoInputId ? { deviceId: { exact: videoInputId } } : { width: 1280, height: 720 },
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play().catch(() => undefined);
      }
      setDevicesOk(true);
      await refreshDevices();
    } catch (e: any) {
      setError(
        e?.name === 'NotAllowedError'
          ? 'Разрешите доступ к камере и микрофону в браузере (или проверьте выбранные устройства).'
          : 'Не удалось запустить предпросмотр устройств.'
      );
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    refreshDevices();
    navigator.mediaDevices?.addEventListener?.('devicechange', refreshDevices);
    return () => {
      navigator.mediaDevices?.removeEventListener?.('devicechange', refreshDevices);
      stopPreview();
    };
  }, []);

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
    try {
      const stream = await streamsAPI.createStream({
        title,
        description,
        visibility,
        allowed_user_ids: visibility === 'private' ? selectedUsers.map((u) => u.id) : [],
      });
      setCurrentStream(stream);
      setTitle('');
      setDescription('');
      setSelectedUsers([]);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || '';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(errorMessage || 'Ошибка создания трансляции');
    } finally {
      setIsCreating(false);
    }
  };

  const handleStartStream = async () => {
    if (!currentStream) return;
    try {
      await streamsAPI.startStream(currentStream.id);
      setCurrentStream({ ...currentStream, is_live: true });
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || 'Ошибка запуска трансляции';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(errorMessage);
    }
  };

  const handleStopStream = async () => {
    if (!currentStream) return;
    try {
      await streamsAPI.stopStream(currentStream.id);
      setCurrentStream({ ...currentStream, is_live: false });
      setError('');
      alert('Трансляция остановлена. Запись будет обработана и появится на канале после кодирования.');
      await loadMyStream();
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || 'Ошибка остановки трансляции';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(errorMessage);
    }
  };

  const rtmpServerUrl = currentStream?.rtmp_server_url || `rtmp://${RTMP_HOST}:${RTMP_PORT}/${RTMP_APP}`;
  const streamKey = currentStream?.rtmp_stream_key || currentStream?.rtmp_key || '';
  const fullRtmp = `${rtmpServerUrl}/${streamKey}`;

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <div className="flex pt-16">
          <Sidebar />
          <main className="flex-1 p-8">
            <div className="text-white text-center py-20">
              <h1 className="text-3xl font-bold mb-4">Войдите для запуска трансляции</h1>
              <button
                onClick={() => router.push('/login')}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
              >
                Войти
              </button>
            </div>
          </main>
        </div>
      </div>
    );
  }

  if (loadingChannel || loadingStream) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
        <Header />
        <div className="flex pt-16">
          <Sidebar />
          <main className="flex-1 p-8">
            <div className="text-white text-center py-20">Загрузка...</div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e]">
      <Header />
      <div className="flex pt-16">
        <Sidebar />
        <main className="flex-1 p-8">
          <div className="max-w-4xl mx-auto space-y-8">
            <h1 className="text-4xl font-bold text-white mb-2">Запустить трансляцию</h1>
            <p className="text-gray-400 text-sm mb-6">
              Настройте микрофон и камеру в браузере (предпросмотр). Для эфира используйте OBS Studio или другой
              RTMP-клиент: укажите сервер и ключ ниже. В OBS: тип источника «Захват экрана» или «Видеозахват» для
              веб-камеры.
            </p>

            {!userChannel && (
              <div className="bg-red-900/30 border border-red-500 rounded-lg p-6 mb-6">
                <p className="text-red-300 mb-4">У вас нет канала. Создайте канал перед запуском трансляции.</p>
                <button
                  onClick={() => router.push('/create-channel')}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                >
                  Создать канал
                </button>
              </div>
            )}

            <section className="bg-[#1a1a3e] rounded-lg p-6 border border-purple-500/30">
              <h2 className="text-xl font-semibold text-white mb-4">Предпросмотр микрофона и камеры</h2>
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-gray-300 text-sm mb-1">Микрофон</label>
                  <select
                    value={audioInputId}
                    onChange={(e) => setAudioInputId(e.target.value)}
                    className="w-full bg-[#0a0a1a] text-white px-3 py-2 rounded border border-purple-500/30"
                  >
                    <option value="">По умолчанию</option>
                    {micDevices.map((d) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label || 'Микрофон'}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-300 text-sm mb-1">Камера</label>
                  <select
                    value={videoInputId}
                    onChange={(e) => setVideoInputId(e.target.value)}
                    className="w-full bg-[#0a0a1a] text-white px-3 py-2 rounded border border-purple-500/30"
                  >
                    <option value="">По умолчанию</option>
                    {camDevices.map((d) => (
                      <option key={d.deviceId} value={d.deviceId}>
                        {d.label || 'Камера'}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex flex-wrap gap-3 mb-4">
                <button
                  type="button"
                  onClick={startPreview}
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
                >
                  Включить предпросмотр
                </button>
                <button
                  type="button"
                  onClick={stopPreview}
                  className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
                >
                  Остановить предпросмотр
                </button>
                {devicesOk && <span className="text-green-400 text-sm self-center">Устройства активны</span>}
              </div>
              <video ref={videoRef} className="w-full max-h-64 rounded-lg bg-black aspect-video" playsInline muted />
            </section>

            {currentStream ? (
              <div className="bg-[#1a1a3e] rounded-lg p-6 border border-purple-500/30">
                <h2 className="text-2xl font-bold text-white mb-4">Текущая трансляция</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-300 mb-2">Название</label>
                    <p className="text-white text-lg">{currentStream.title}</p>
                  </div>
                  {currentStream.description && (
                    <div>
                      <label className="block text-gray-300 mb-2">Описание</label>
                      <p className="text-white">{currentStream.description}</p>
                    </div>
                  )}
                  <div>
                    <label className="block text-gray-300 mb-2">Видимость</label>
                    <p className="text-white">
                      {currentStream.visibility === 'private' ? 'Приватная (по списку)' : 'Только сотрудники ДГИ'}
                    </p>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-2">RTMP сервер (OBS: «Сервер»)</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={rtmpServerUrl}
                        readOnly
                        className="flex-1 bg-[#0a0a1a] text-white px-4 py-2 rounded border border-purple-500/30 text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(rtmpServerUrl)}
                        className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
                      >
                        Копировать
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-2">Ключ потока (OBS: «Ключ потока»)</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={streamKey}
                        readOnly
                        className="flex-1 bg-[#0a0a1a] text-white px-4 py-2 rounded border border-purple-500/30 font-mono text-sm"
                      />
                      <button
                        type="button"
                        onClick={() => navigator.clipboard.writeText(streamKey)}
                        className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
                      >
                        Копировать
                      </button>
                    </div>
                  </div>
                  <div className="bg-[#0a0a1a] rounded p-4 border border-purple-500/30">
                    <p className="text-gray-300 mb-2">Полный RTMP URL (некоторые программы):</p>
                    <code className="text-purple-400 text-sm break-all">{fullRtmp}</code>
                  </div>
                  <p className="text-amber-200/90 text-sm">
                    Сначала нажмите «Разрешить эфир», затем в OBS нажмите «Начать трансляцию». Пока эфир не разрешён
                    с сервера, MediaMTX отклонит публикацию.
                  </p>
                  <div className="flex flex-wrap gap-4">
                    {currentStream.is_live ? (
                      <button
                        type="button"
                        onClick={handleStopStream}
                        className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                      >
                        Остановить и сохранить на канал
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={handleStartStream}
                        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                      >
                        Разрешить эфир (затем OBS → Начать трансляцию)
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => router.push(`/stream/${currentStream.id}`)}
                      className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                    >
                      Открыть страницу просмотра (HLS)
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateStream} className="space-y-6 bg-[#1a1a3e]/50 rounded-lg p-6 border border-purple-500/20">
                <div>
                  <label className="block text-gray-300 mb-2">Название трансляции *</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full bg-[#0a0a1a] text-white px-4 py-3 rounded border border-purple-500/30 focus:border-purple-500 focus:outline-none"
                    placeholder="Введите название трансляции"
                    required
                  />
                </div>
                <div>
                  <label className="block text-gray-300 mb-2">Описание</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full bg-[#0a0a1a] text-white px-4 py-3 rounded border border-purple-500/30 focus:border-purple-500 focus:outline-none"
                    placeholder="Описание трансляции (необязательно)"
                    rows={4}
                  />
                </div>
                <div>
                  <label className="block text-gray-300 mb-2">Кто может смотреть</label>
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 text-gray-200 cursor-pointer">
                      <input
                        type="radio"
                        name="vis"
                        checked={visibility === 'dgi_employees'}
                        onChange={() => setVisibility('dgi_employees')}
                        className="accent-purple-600"
                      />
                      Только сотрудники ДГИ (по флагу учётной записи)
                    </label>
                    <label className="flex items-center gap-2 text-gray-200 cursor-pointer">
                      <input
                        type="radio"
                        name="vis"
                        checked={visibility === 'private'}
                        onChange={() => setVisibility('private')}
                        className="accent-purple-600"
                      />
                      Приватная — только выбранные пользователи
                    </label>
                  </div>
                </div>

                {visibility === 'private' && (
                  <div className="border border-purple-500/30 rounded-lg p-4 bg-[#0a0a1a]/50">
                    <label className="block text-gray-300 mb-2">Зрители (поиск по логину, мин. 2 символа)</label>
                    <input
                      type="text"
                      value={userSearchQuery}
                      onChange={(e) => setUserSearchQuery(e.target.value)}
                      placeholder="Поиск пользователя..."
                      className="w-full bg-[#0a0a1a] text-white px-4 py-2 rounded border border-purple-500/30 mb-2"
                    />
                    {isSearching && <p className="text-gray-500 text-sm">Поиск...</p>}
                    {searchResults.length > 0 && (
                      <ul className="max-h-40 overflow-y-auto border border-purple-500/20 rounded mb-3">
                        {searchResults.map((u) => (
                          <li key={u.id}>
                            <button
                              type="button"
                              onClick={() => addUser(u)}
                              className="w-full text-left px-3 py-2 text-sm text-white hover:bg-purple-600/40"
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
                          className="inline-flex items-center gap-1 bg-purple-900/50 text-white text-sm px-2 py-1 rounded"
                        >
                          {u.username}
                          <button type="button" className="text-red-300 hover:text-red-100" onClick={() => removeUser(u.id)}>
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {error && (
                  <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
                    <p className="text-red-300">{typeof error === 'string' ? error : JSON.stringify(error)}</p>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={isCreating || !userChannel}
                  className="w-full px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isCreating ? 'Создание...' : 'Создать трансляцию'}
                </button>
              </form>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
