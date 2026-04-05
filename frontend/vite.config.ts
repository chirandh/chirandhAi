import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const api = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/sessions": { target: api, changeOrigin: true },
      "/jobs": { target: api, changeOrigin: true },
      "/artifacts": { target: api, changeOrigin: true },
      "/health": { target: api, changeOrigin: true },
      "/ready": { target: api, changeOrigin: true },
    },
  },
});
