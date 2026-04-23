import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    server: {
        port: 5173,
        proxy: {
            // FR-2 / FR-6 / FR-8 endpoints all live on the FastAPI backend during dev.
            "/healthz": "http://127.0.0.1:8000",
            "/library": "http://127.0.0.1:8000",
            "/run": "http://127.0.0.1:8000",
            "/results": "http://127.0.0.1:8000",
            "/preflight": "http://127.0.0.1:8000",
        },
    },
});
