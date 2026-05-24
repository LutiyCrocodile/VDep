'use client';

import { useEffect } from 'react';
import { getPortalLoginUrl } from '@/lib/portal-url';

export default function LoginPage() {
  useEffect(() => {
    window.location.href = getPortalLoginUrl();
  }, []);

  return (
    <div className="min-h-screen bg-dgi-bg flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-dgi-primary" />
    </div>
  );
}
