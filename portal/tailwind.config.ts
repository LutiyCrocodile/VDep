import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        dgi: {
          primary: '#1e3a8a',      // Тёмно-синий (корпоративный)
          secondary: '#3b82f6',   // Синий
          accent: '#60a5fa',        // Светло-синий
          dark: '#0f172a',          // Тёмный фон
          light: '#f8fafc',         // Светлый фон
        }
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
      },
    },
  },
  plugins: [],
}
export default config
