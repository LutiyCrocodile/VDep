'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/services/auth';
import { useState, useEffect } from 'react';
import { channelsAPI } from '@/services/api';

const menuItems = [
  { icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', label: 'Главная', href: '/' },
  { icon: 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z M21 12a9 9 0 11-18 0 9 9 0 0118 0z', label: 'Подписки', href: '/subscriptions' },
];

const getUserMenuItems = (channel: any) => [
  { icon: 'M4 6h16M4 12h16M4 18h16', label: 'Мой канал', href: channel ? `/channel/${channel.handle}` : '/channel' },
  { icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z', label: 'Запустить трансляцию', href: '/go-live' },
  { icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', label: 'История', href: '/history' },
  { icon: 'M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zM6.293 6.707a1 1 0 010-1.414l3-3a1 1 0 011.414 0l3 3a1 1 0 01-1.414 1.414L11 5.414V13a1 1 0 11-2 0V5.414L7.707 6.707a1 1 0 01-1.414 0z', label: 'Мои видео', href: '/my-videos' },
  { icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z', label: 'Смотреть позже', href: '/watch-later' },
  { icon: 'M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z', label: 'Понравившиеся', href: '/liked' },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { isAuthenticated, logout } = useAuth();
  const [userChannel, setUserChannel] = useState<any>(null);

  useEffect(() => {
    const fetchChannel = async () => {
      if (isAuthenticated) {
        try {
          const channel = await channelsAPI.getUserChannel();
          setUserChannel(channel);
        } catch {
          setUserChannel(null);
        }
      }
    };
    fetchChannel();
  }, [isAuthenticated]);

  return (
    <aside className="fixed left-0 top-14 h-[calc(100vh-56px)] w-64 bg-[#0a0a1a] overflow-y-auto z-40 border-r border-[#27274a]">
      <div className="py-3">
        <ul className="space-y-1 px-3">
          {menuItems.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`flex items-center gap-4 px-3 py-2 rounded-xl transition-all duration-200 ${
                  pathname === item.href
                    ? 'bg-gradient-to-r from-indigo-600/20 to-violet-600/20 text-white border border-indigo-500/30'
                    : 'text-zinc-400 hover:bg-[#252550] hover:text-white'
                }`}
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            </li>
          ))}
        </ul>

        <hr className="my-3 border-[#27274a]" />

        {isAuthenticated && (
          <>
            <div className="px-6 py-2">
              <h3 className="text-sm font-medium text-zinc-500">Вы</h3>
            </div>
            <ul className="space-y-1 px-3">
              {getUserMenuItems(userChannel).map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`flex items-center gap-4 px-3 py-2 rounded-xl transition-all duration-200 ${
                      pathname === item.href
                        ? 'bg-gradient-to-r from-indigo-600/20 to-violet-600/20 text-white border border-indigo-500/30'
                        : 'text-zinc-400 hover:bg-[#252550] hover:text-white'
                    }`}
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                    </svg>
                    <span className="text-sm font-medium">{item.label}</span>
                  </Link>
                </li>
              ))}
            </ul>
            <hr className="my-3 border-[#27274a]" />
          </>
        )}

        <div className="px-6 py-2">
          <h3 className="text-sm font-medium text-zinc-500">Настройки</h3>
        </div>
        <ul className="space-y-1 px-3">
          {isAuthenticated && (
            <li>
              <button
                onClick={logout}
                className="w-full flex items-center gap-4 px-3 py-2 rounded-xl text-zinc-400 hover:bg-[#252550] hover:text-white transition-all duration-200"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                <span className="text-sm font-medium">Выйти</span>
              </button>
            </li>
          )}
        </ul>
      </div>
    </aside>
  );
}
