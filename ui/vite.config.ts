import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/ui/',
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
  server: {
    host: '0.0.0.0',  // Allow external connections
    port: 3000,
    proxy: {
      '/redfish': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
})
