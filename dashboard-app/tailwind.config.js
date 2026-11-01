/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Mukta', '"Noto Sans Devanagari"', 'system-ui', 'sans-serif'],
        head: ['"Noto Sans Devanagari"', 'Mukta', 'system-ui', 'sans-serif'],
      },
      colors: {
        navy: {
          50: '#eef2f9', 100: '#d6dff0', 200: '#adbfe0', 300: '#7f99c9', 400: '#5574ad',
          500: '#3a5892', 600: '#2b4477', 700: '#22365f', 800: '#1a2a4a', 900: '#121e36', 950: '#0b1324',
        },
        saffron: { 400: '#f5a54a', 500: '#ee8a1c', 600: '#c96f0e' },
      },
      minHeight: { tap: '44px' },
      minWidth: { tap: '44px' },
    },
  },
  plugins: [],
};
