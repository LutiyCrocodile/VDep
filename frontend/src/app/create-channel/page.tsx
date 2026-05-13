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
      <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e] flex items-center justify-center">
        <div className="text-white">Войдите в систему для создания канала</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#0a0a1a] to-[#1a1a3e] py-12 px-4">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-4xl font-bold text-white mb-8">Создать канал</h1>
        
        <div className="bg-[#1a1a3e]/50 backdrop-blur-sm rounded-2xl p-8 border border-[#4f46e5]/30">
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Название канала
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-3 bg-[#0a0a1a]/50 border border-[#4f46e5]/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50"
                placeholder="Мой канал"
                required
              />
            </div>

            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Описание
              </label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="w-full px-4 py-3 bg-[#0a0a1a]/50 border border-[#4f46e5]/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 min-h-[120px]"
                placeholder="О чем ваш канал..."
              />
            </div>

            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Имя пользователя (handle)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">@</span>
                <input
                  type="text"
                  value={formData.handle}
                  onChange={(e) => setFormData({ ...formData, handle: e.target.value })}
                  className="w-full pl-8 pr-4 py-3 bg-[#0a0a1a]/50 border border-[#4f46e5]/30 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50"
                  placeholder="mychannel"
                  required
                />
              </div>
              <p className="text-gray-400 text-sm mt-2">
                Это будет ваш уникальный идентификатор канала
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-[#4f46e5] to-[#7c3aed] text-white font-semibold rounded-lg hover:from-[#4338ca] hover:to-[#6d28d9] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Создание...' : 'Создать канал'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
