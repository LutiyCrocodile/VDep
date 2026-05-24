'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/services/auth';
import Link from 'next/link';
import Image from 'next/image';

export default function RegisterForm() {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    full_name: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();
  const { register, login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await register(formData);
      await login(formData.username, formData.password);
      router.push('/');
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: unknown } } };
      const detail = axiosErr.response?.data?.detail;
      const errorMessage = typeof detail === 'string' ? detail : (detail ? JSON.stringify(detail) : 'Ошибка регистрации');
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center dgi-gradient-bg">
      <div className="bg-dgi-surface p-8 rounded-2xl shadow-lg w-full max-w-md border border-dgi-border">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Image src="/icon.ico" alt="" width={48} height={48} className="rounded-xl shadow-md" priority />
            <span className="text-2xl font-bold text-dgi-text font-heading">Видеохостинг ДГИ</span>
          </div>
          <h1 className="text-2xl font-semibold text-dgi-text font-heading">Регистрация</h1>
          <p className="text-dgi-muted mt-2">Создайте новый аккаунт</p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl mb-4 text-sm">
            {typeof error === 'string' ? error : JSON.stringify(error)}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">Имя пользователя</label>
            <input
              type="text"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              className="dgi-input"
              placeholder="Введите имя пользователя"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="dgi-input"
              placeholder="email@example.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">Полное имя</label>
            <input
              type="text"
              value={formData.full_name}
              onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
              className="dgi-input"
              placeholder="Иван Иванов"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-dgi-text mb-2">Пароль</label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              className="dgi-input"
              placeholder="Введите пароль"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="dgi-btn-primary w-full font-semibold py-3 px-4 rounded-xl disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Регистрация...' : 'Зарегистрироваться'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-dgi-muted">
            Уже есть аккаунт?{' '}
            <Link href="/login" className="text-dgi-primary hover:text-dgi-primary-mid font-medium transition-colors">
              Войти
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
