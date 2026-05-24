import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['var(--dgi-font-heading)'],
        sans: ['var(--dgi-font-body)'],
      },
      colors: {
        dgi: {
          primary: 'rgb(var(--dgi-primary-rgb) / <alpha-value>)',
          'primary-mid': 'rgb(var(--dgi-primary-mid-rgb) / <alpha-value>)',
          'primary-dark': 'rgb(var(--dgi-primary-dark-rgb) / <alpha-value>)',
          bg: 'var(--dgi-bg)',
          surface: 'var(--dgi-surface)',
          'surface-hover': 'var(--dgi-surface-hover)',
          border: 'var(--dgi-border)',
          text: 'var(--dgi-text)',
          muted: 'var(--dgi-text-muted)',
        },
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
