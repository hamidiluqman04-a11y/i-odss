import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the React app runs on http://localhost:5173 and forwards
// every /api request to Django. To the browser both look like the same
// website, so login cookies work and no CORS setup is needed.
// Django is on port 8000 unless IODSS_API_URL says otherwise (start.ps1 sets
// it when 8000 is already taken by another program).
const apiUrl = process.env.IODSS_API_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // changeOrigin: false keeps the browser's Host header, so Django sees
      // the request as same-origin and its CSRF check passes on any dev port.
      "/api": { target: apiUrl, changeOrigin: false },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/setupTests.js",
    css: false,
  },
});
