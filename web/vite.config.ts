import { defineConfig } from 'vite';

// Relative base so the static build works under any sub-path (GitHub Pages).
export default defineConfig({
  base: './',
  build: { outDir: 'dist', target: 'es2022', chunkSizeWarningLimit: 900 },
  test: { environment: 'node' },
});
