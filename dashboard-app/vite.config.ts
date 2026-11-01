import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev: proxy /api to a locally running `wrangler dev` (port 8787). No URL or key is stored here.
export default defineConfig({
  plugins: [react()],
  build: { target: 'es2022', outDir: 'dist', chunkSizeWarningLimit: 1500 },
  server: { proxy: { '/api': 'http://127.0.0.1:8787' } },
  preview: { proxy: { '/api': 'http://127.0.0.1:8787' } },
});
