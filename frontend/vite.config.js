import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the API is proxied to a local backend; in containers nginx
// (compose) or the ingress (kubernetes) does the same job.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
});
