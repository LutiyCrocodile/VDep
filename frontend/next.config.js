/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8005',
  },
  async rewrites() {
    return [
      // Proxy HLS videos to video-service (through nginx)
      {
        source: '/videos/:path*',
        destination: 'http://localhost/videos/:path*',
      },
    ];
  },
}

module.exports = nextConfig
