import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// claude.ai artifact build: the whole app in ONE html (dist-artifact/index.html), data layer = src/lib/artifact (VITE_BACKEND).
export default defineConfig({
  plugins: [react(), viteSingleFile({ removeViteModuleLoader: true })],
  define: {
    'import.meta.env.VITE_BACKEND': JSON.stringify('artifact'),
    // the published page's own link (WhatsApp share text, E-F6); override with VITE_PAGE_URL=… for another page
    'import.meta.env.VITE_PAGE_URL': JSON.stringify(process.env.VITE_PAGE_URL || 'https://claude.ai/artifact/8cJP8wz6j5tYM5kRHK1rVx'),
  },
  build: { target: 'es2022', outDir: 'dist-artifact', assetsInlineLimit: 100_000_000, cssCodeSplit: false, chunkSizeWarningLimit: 20000 },
});
