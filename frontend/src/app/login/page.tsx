'use client';

import { useEffect } from 'react';
import { getPortalLoginUrl } from '@/lib/portal-url';

export default function LoginPage() {
  useEffect(() => {
    window.location.href = getPortalLoginUrl();
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0a1a] flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-indigo-500" />
    </div>
  );
}
