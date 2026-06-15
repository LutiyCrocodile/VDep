import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const apiTarget = process.env.VITE_API_PROXY || 'http://localhost:8005'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3005,
    host: true,
    proxy: {
      '/api': apiTarget,
      '/ws': { target: apiTarget.replace(/^http/, 'ws'), ws: true },
      '/uploads': apiTarget,
    },
  },
})
