/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/auth/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ]
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
