'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import { streamsAPI, channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

export default function GoLivePage() {
  const router = useRouter();
  const { user } = useAuth();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');
  const [userChannel, setUserChannel] = useState<any>(null);
  const [loadingChannel, setLoadingChannel] = useState(true);
  const [currentStream, setCurrentStream] = useState<any>(null);
  const [loadingStream, setLoadingStream] = useState(false);

  useEffect(() => {
    if (user) {
      fetchUserChannel();
      fetchCurrentStream();
    }
  }, [user]);

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

  const fetchCurrentStream = async () => {
    try {
      const streams = await streamsAPI.getStreams();
      if (streams && streams.length > 0) {
        const userStream = streams.find((s: any) => s.user_id === user?.id && s.is_live);
        if (userStream) {
          setCurrentStream(userStream);
        }
      }
    } catch (err) {
      console.error('Error fetching stream:', err);
    } finally {
      setLoadingStream(false);
    }
  };

  const handleCreateStream = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;

    if (!userChannel) {
      setError('Сначала создайте канал для запуска трансляции');
      return;
    }

    setIsCreating(true);
    setError('');
    try {
      const stream = await streamsAPI.createStream({
        title,
        description,
        is_private: isPrivate
      });
      setCurrentStream(stream);
      setTitle('');
      setDescription('');
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || '';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      if (err.response?.status === 403 && errorMessage.includes('channel')) {
        setError('У вас нет канала. Создайте канал перед запуском трансляции.');
        setUserChannel(null);
      } else {
        setError(errorMessage || 'Ошибка создания трансляции');
      }
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
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || 'Ошибка остановки трансляции';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(errorMessage);
    }
  };

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
          <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl font-bold text-white mb-8">Запустить трансляцию</h1>

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
                    <label className="block text-gray-300 mb-2">RTMP ключ</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={currentStream.rtmp_key}
                        readOnly
                        className="flex-1 bg-[#0a0a1a] text-white px-4 py-2 rounded border border-purple-500/30"
                      />
                      <button
                        onClick={() => navigator.clipboard.writeText(currentStream.rtmp_key)}
                        className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
                      >
                        Копировать
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="block text-gray-300 mb-2">RTMP URL</label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value="rtmp://localhost:1935/live"
                        readOnly
                        className="flex-1 bg-[#0a0a1a] text-white px-4 py-2 rounded border border-purple-500/30"
                      />
                      <button
                        onClick={() => navigator.clipboard.writeText('rtmp://localhost:1935/live')}
                        className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 transition"
                      >
                        Копировать
                      </button>
                    </div>
                  </div>
                  <div className="bg-[#0a0a1a] rounded p-4 border border-purple-500/30">
                    <p className="text-gray-300 mb-2">Полный URL для OBS:</p>
                    <code className="text-purple-400 text-sm">
                      rtmp://localhost:1935/live/{currentStream.rtmp_key}
                    </code>
                  </div>
                  <div className="flex gap-4">
                    {currentStream.is_live ? (
                      <button
                        onClick={handleStopStream}
                        className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition"
                      >
                        Остановить трансляцию
                      </button>
                    ) : (
                      <button
                        onClick={handleStartStream}
                        className="px-6 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
                      >
                        Начать трансляцию
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreateStream} className="space-y-6">
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
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="private"
                    checked={isPrivate}
                    onChange={(e) => setIsPrivate(e.target.checked)}
                    className="w-5 h-5 accent-purple-600"
                  />
                  <label htmlFor="private" className="text-gray-300">
                    Приватная трансляция
                  </label>
                </div>
                {error && (
                  <div className="bg-red-900/30 border border-red-500 rounded-lg p-4">
                    <p className="text-red-300">{typeof error === 'string' ? error : JSON.stringify(error)}</p>
                  </div>
                )}
                <button
                  type="submit"
                  disabled={isCreating}
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
