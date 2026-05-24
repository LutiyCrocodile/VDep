'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { notificationsAPI } from '@/services/api';
import { useAuth } from '@/services/auth-context';

type NotificationItem = {
  id: string;
  type: string;
  message: string;
  data?: {
    link_path?: string;
    event_type?: string;
  } | null;
  is_read: boolean;
  created_at: string;
};

function formatTime(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'только что';
  if (mins < 60) return `${mins} мин. назад`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ч. назад`;
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

export default function NotificationDropdown() {
  const { isAuthenticated } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const refreshUnread = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await notificationsAPI.getUnreadCount();
      setUnreadCount(data.unread_count ?? 0);
    } catch {
      /* ignore */
    }
  }, [isAuthenticated]);

  const loadNotifications = useCallback(async () => {
    if (!isAuthenticated) return;
    setLoading(true);
    try {
      const data = await notificationsAPI.getNotifications(0, 30);
      setItems(Array.isArray(data) ? data : []);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    refreshUnread();
    const interval = setInterval(refreshUnread, 30000);
    return () => clearInterval(interval);
  }, [refreshUnread]);

  useEffect(() => {
    if (open) {
      loadNotifications();
      refreshUnread();
    }
  }, [open, loadNotifications, refreshUnread]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const handleItemClick = async (n: NotificationItem) => {
    if (!n.is_read) {
      try {
        await notificationsAPI.markAsRead(n.id);
        setUnreadCount((c) => Math.max(0, c - 1));
        setItems((prev) =>
          prev.map((x) => (x.id === n.id ? { ...x, is_read: true } : x))
        );
      } catch {
        /* ignore */
      }
    }
    setOpen(false);
    const path = n.data?.link_path;
    if (path) router.push(path);
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      setUnreadCount(0);
      setItems((prev) => prev.map((x) => ({ ...x, is_read: true })));
    } catch {
      /* ignore */
    }
  };

  if (!isAuthenticated) return null;

  return (
    <div className="relative" ref={panelRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 hover:bg-dgi-surface-hover rounded-full transition-all duration-200"
        aria-label="Уведомления"
      >
        <svg
          className="w-6 h-6 text-dgi-text"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-dgi-primary text-white text-[10px] font-bold leading-none">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[380px] max-h-[min(70vh,480px)] bg-dgi-surface border border-dgi-border rounded-xl shadow-xl z-[60] flex flex-col overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-dgi-border">
            <h3 className="font-semibold text-dgi-text font-heading">Уведомления</h3>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                className="text-xs text-dgi-primary hover:underline"
              >
                Прочитать все
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1">
            {loading ? (
              <div className="flex justify-center py-10">
                <div className="w-6 h-6 border-2 border-dgi-primary border-t-transparent rounded-full animate-spin" />
              </div>
            ) : items.length === 0 ? (
              <p className="text-dgi-muted text-sm text-center py-10 px-4">
                Пока нет уведомлений. Подпишитесь на каналы — вы узнаете о новых видео и эфирах.
              </p>
            ) : (
              <ul className="divide-y divide-dgi-border">
                {items.map((n) => (
                  <li key={n.id}>
                    <button
                      type="button"
                      onClick={() => handleItemClick(n)}
                      className={`w-full text-left px-4 py-3 hover:bg-dgi-surface-hover transition-colors ${
                        !n.is_read ? 'bg-dgi-primary/5' : ''
                      }`}
                    >
                      <div className="flex gap-2">
                        {!n.is_read && (
                          <span className="w-2 h-2 rounded-full bg-dgi-primary mt-2 flex-shrink-0" />
                        )}
                        <div className={!n.is_read ? '' : 'ml-4'}>
                          <p className="text-sm text-dgi-text leading-snug">{n.message}</p>
                          <p className="text-xs text-dgi-muted mt-1">
                            {n.type === 'stream_live' ? 'Эфир' : 'Новое видео'} · {formatTime(n.created_at)}
                          </p>
                        </div>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="border-t border-dgi-border px-4 py-2">
            <Link
              href="/subscriptions"
              onClick={() => setOpen(false)}
              className="text-xs text-dgi-primary hover:underline"
            >
              Мои подписки
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
