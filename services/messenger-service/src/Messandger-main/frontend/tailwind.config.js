/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Century Gothic"', 'CenturyGothic', 'AppleGothic', '"URW Gothic"', 'Arial', 'sans-serif'],
        heading: ['"Century Gothic"', 'CenturyGothic', '"URW Gothic"', 'Arial', 'sans-serif'],
        accent: ['Arial', '"Helvetica Neue"', 'Helvetica', 'sans-serif'],
      },
      colors: {
        primary: {
          50: '#fdecee', 100: '#fad1d5', 200: '#f5a3aa', 300: '#ee7079',
          400: '#db404a', 500: '#c8141e', 600: '#aa141e', 700: '#8c141e',
          800: '#6e1218', 900: '#4a0d11', 950: '#2a0709',
        },
        dark: {
          50: '#f5f5f5', 100: '#e5e5e5', 200: '#c7c7c7', 300: '#a3a3a3',
          400: '#757575', 500: '#525252', 600: '#3a3a3a', 700: '#2a2a2a',
          800: '#1f1f1f', 900: '#141414', 950: '#0a0a0a',
        },
        brand: {
          red: '#aa141e',
          'red-bright': '#c8141e',
          'red-dark': '#8c141e',
          black: '#141414',
        },
      },
    },
  },
  plugins: [],
}
