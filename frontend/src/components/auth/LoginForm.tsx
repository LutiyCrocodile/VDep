'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/services/auth';
import Link from 'next/link';

export default function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      router.push('/');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : 'Неверное имя пользователя или пароль');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen dgi-gradient-bg flex items-center justify-center">
      <div className="bg-dgi-surface rounded-2xl p-8 shadow-lg w-full max-w-md border border-dgi-border">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 bg-gradient-to-br from-dgi-primary to-dgi-primary-mid rounded-xl flex items-center justify-center">
              <svg className="w-7 h-7 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" />
              </svg>
            </div>
            <div className="text-left">
              <span className="text-xl font-bold text-dgi-text font-heading">Видеохостинг ДГИ</span>
              <p className="text-xs text-dgi-muted">Корпоративная платформа</p>
            </div>
          </div>
          <h1 className="text-2xl font-semibold text-dgi-text font-heading">Вход</h1>
          <p className="text-dgi-muted mt-2">Войдите в свой аккаунт</p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl mb-4">
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">
              Имя пользователя
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-3 bg-dgi-bg border border-dgi-border rounded-xl text-dgi-text placeholder-zinc-500 focus:outline-none focus:border-dgi-primary/50 focus:ring-2 focus:ring-dgi-primary/20 transition-all"
              placeholder="Введите имя пользователя"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">
              Пароль
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 bg-dgi-bg border border-dgi-border rounded-xl text-dgi-text placeholder-zinc-500 focus:outline-none focus:border-dgi-primary/50 focus:ring-2 focus:ring-dgi-primary/20 transition-all"
              placeholder="Введите пароль"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="dgi-btn-primary w-full font-semibold py-3 px-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                </svg>
                Вход...
              </span>
            ) : 'Войти'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-dgi-muted">
            Нет аккаунта?{' '}
            <Link href="/register" className="text-dgi-primary hover:text-dgi-primary-mid font-medium transition-colors">
              Зарегистрироваться
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
