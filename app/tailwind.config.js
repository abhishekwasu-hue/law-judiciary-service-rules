/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: { sans: ['"Noto Sans Devanagari"', 'system-ui', 'sans-serif'] },
      colors: {
        navy: { 50: '#eef3fb', 100: '#d6e1f3', 500: '#2f5596', 600: '#244681', 700: '#1e3a6e', 800: '#172d55', 900: '#0f1b33' },
        saffron: { 400: '#f2a54a', 500: '#e8892b', 600: '#c96f17' },
      },
    },
  },
  plugins: [],
};
