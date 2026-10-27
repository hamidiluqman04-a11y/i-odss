import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the React app runs on http://localhost:5173 and forwards
// every /api request to Django on port 8000. To the browser both look like the
// same website, so login cookies work and no CORS setup is needed.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // changeOrigin: false keeps the browser's Host header, so Django sees
      // the request as same-origin and its CSRF check passes on any dev port.
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.js",
    css: false,
  },
});
