import { defineConfig } from "vite";

const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:8000";
const proxiedPaths = ["/health", "/auth", "/domains", "/schedules", "/submissions", "/reports", "/admin", "/data"];
const allowedHosts = (process.env.VITE_ALLOWED_HOSTS ?? "crabins-macbook")
  .split(",")
  .map((host) => host.trim())
  .filter(Boolean);

export default defineConfig({
  server: {
    allowedHosts,
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
