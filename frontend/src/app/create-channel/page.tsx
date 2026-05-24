'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { channelsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

export default function CreateChannelPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    handle: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await channelsAPI.createChannel(formData);
      router.push('/');
    } catch (err: any) {
      console.error('Create channel error:', err);
      const errorDetail = err.response?.data?.detail || err.message || 'Ошибка создания канала';
      const errorMessage = typeof errorDetail === 'string' ? errorDetail : JSON.stringify(errorDetail);
      setError(`Ошибка: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen dgi-gradient-bg flex items-center justify-center">
        <div className="text-dgi-text">Войдите в систему для создания канала</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen dgi-gradient-bg py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-dgi-text mb-8 font-heading">Создать канал</h1>
        
        <div className="dgi-card p-8">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6 text-sm">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-dgi-text text-sm font-medium mb-2">
                Название канала
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="dgi-input"
                placeholder="Мой канал"
                required
              />
            </div>

            <div>
              <label className="block text-dgi-text text-sm font-medium mb-2">
                Описание
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="dgi-input min-h-[120px]"
                placeholder="О чем ваш канал..."
              />
            </div>

            <div>
              <label className="block text-dgi-text text-sm font-medium mb-2">
                Имя пользователя (handle)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-dgi-muted">@</span>
                <input
                  type="text"
                  value={formData.handle}
                  onChange={(e) => setFormData({ ...formData, handle: e.target.value })}
                  className="dgi-input pl-8"
                  placeholder="mychannel"
                  required
                />
              </div>
              <p className="text-dgi-muted text-sm mt-2">
                Это будет ваш уникальный идентификатор канала
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="dgi-btn-primary w-full py-3 font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Создание...' : 'Создать канал'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
