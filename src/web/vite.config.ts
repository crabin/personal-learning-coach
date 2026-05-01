import { defineConfig } from "vite";

const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const proxiedPaths = ["/health", "/domains", "/schedules", "/submissions", "/reports", "/admin", "/data"];

export default defineConfig({
  server: {
    port: 5173,
    strictPort: false,
    proxy: Object.fromEntries(
      proxiedPaths.map((path) => [
        path,
        {
          target: apiTarget,
          changeOrigin: true,
        },
      ]),
    ),
  },
});
