'use client';

import { useEffect } from 'react';

export default function RegisterPage() {
  useEffect(() => {
    window.location.href = 'http://localhost:3002/login';
  }, []);

  return (
    <div className="min-h-screen bg-dgi-bg flex items-center justify-center">
      <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-dgi-primary" />
    </div>
  );
}
