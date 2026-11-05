import { defineConfig, Plugin, type Connect } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { createServer } from "./server";

// Python quant API (FastAPI). The browser only ever talks to Vite; /api/v1 is proxied.
export const QUANT_API_URL = process.env.QUANT_API_URL ?? "http://127.0.0.1:8765"; // 8765: avoids the very common 8000 (Docker, etc.)

// https://vitejs.dev/config/
export default defineConfig(() => ({
  server: {
    // Local only by default; set VITE_DEV_HOST="::" explicitly to expose it (e.g. cloud dev box).
    host: process.env.VITE_DEV_HOST ?? "localhost",
    port: 8080,
    fs: {
      allow: ["./client", "./shared"],
      deny: [".env", ".env.*", "*.{crt,pem}", "**/.git/**", "server/**"],
    },
    proxy: {
      "/api/v1": { target: QUANT_API_URL, changeOrigin: false },
    },
  },
  build: {
    outDir: "dist/spa",
  },
  plugins: [react(), expressPlugin()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./client"),
      "@shared": path.resolve(__dirname, "./shared"),
    },
  },
}));

function expressPlugin(): Plugin {
  return {
    name: "express-plugin",
    apply: "serve", // Only apply during development (serve mode)
    configureServer(server) {
      // An Express app is a Connect-compatible handler.
      const app = createServer() as unknown as Connect.NextHandleFunction;

      // Add Express app as middleware to Vite dev server — except for /api/v1, which belongs
      // to the Python API (express.json() would otherwise consume POST bodies before the proxy).
      server.middlewares.use((req, res, next) => {
        if (req.url?.startsWith("/api/v1")) return next();
        return app(req, res, next);
      });
    },
  };
}
