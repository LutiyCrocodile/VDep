/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    // Локально: 127.0.0.1:8000. В образе portal задаётся AUTH_INTERNAL_URL (см. portal/Dockerfile).
    const authInternal =
      process.env.AUTH_INTERNAL_URL || 'http://127.0.0.1:8000';
    return [
      {
        source: '/api/auth/:path*',
        destination: `${authInternal.replace(/\/$/, '')}/api/v1/:path*`,
      },
    ];
  },
  env: {
    NEXT_PUBLIC_VIDEO_URL: process.env.NEXT_PUBLIC_VIDEO_URL || 'http://localhost:3000',
    NEXT_PUBLIC_AUTH_URL: process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000',
    NEXT_PUBLIC_MESSENGER_URL: process.env.NEXT_PUBLIC_MESSENGER_URL || '#',
    NEXT_PUBLIC_DASHBOARD_URL: process.env.NEXT_PUBLIC_DASHBOARD_URL || '#',
    NEXT_PUBLIC_SUPPORT_URL: process.env.NEXT_PUBLIC_SUPPORT_URL || '#',
  }
}

module.exports = nextConfig
