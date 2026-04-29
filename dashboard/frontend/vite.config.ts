import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import fs from "node:fs/promises";

const BACKEND = "http://127.0.0.1:8000";

// API path prefixes that the frontend also uses as SPA routes (e.g. /library
// is a NavLink AND /library/summary is a backend endpoint). Without help, a
// browser refresh on /library would be proxied to FastAPI and either 404 or
// return JSON. This regex matches the navigation requests we need to intercept.
const SHADOWED_ROUTE = /^\/(library|run|results)(\/.*)?$/;

// Intercept browser navigations (Accept: text/html) to shadowed paths and serve
// the Vite-transformed index.html, so React Router can take over client-side.
// Runs before the proxy because it's installed during configureServer's
// synchronous body, ahead of Vite's internal middlewares.
function spaFallbackForShadowedRoutes(): Plugin {
  return {
    name: "trend-spa-fallback",
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (req.method !== "GET") return next();
        const accept = req.headers.accept ?? "";
        if (!accept.includes("text/html")) return next();
        const url = req.url ?? "/";
        const pathname = url.split("?")[0];
        if (!SHADOWED_ROUTE.test(pathname)) return next();
        try {
          const indexPath = path.resolve(__dirname, "index.html");
          const raw = await fs.readFile(indexPath, "utf-8");
          const html = await server.transformIndexHtml(url, raw);
          res.setHeader("Content-Type", "text/html");
          res.statusCode = 200;
          res.end(html);
        } catch (err) {
          next(err);
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [spaFallbackForShadowedRoutes(), react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/healthz": BACKEND,
      "/preflight": BACKEND,
      "/library": BACKEND,
      "/run": BACKEND,
      "/results": BACKEND,
    },
  },
});
