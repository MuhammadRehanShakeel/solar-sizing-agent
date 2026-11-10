import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The browser only talks to http://localhost:5175; Vite forwards /api/* to FastAPI on 5002.
// (5173/5000 = FYP, 5174/5001 = RoadGuard, 5175/5002 = SolarSaathi: they never clash.)
//
// PHONE=1 (start_phone.bat): serve over HTTPS on the Wi-Fi network, because phone browsers
// only allow the MICROPHONE on HTTPS pages.
const phone = process.env.PHONE === '1';

export default defineConfig(async () => ({
  plugins: [react(), ...(phone ? [(await import('@vitejs/plugin-basic-ssl')).default()] : [])],
  server: {
    port: 5175,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
  build: { chunkSizeWarningLimit: 1500 },
}));
