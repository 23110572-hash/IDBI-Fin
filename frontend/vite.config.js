import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// The SPA calls the backend directly using VITE_API_BASE (see src/lib/api.ts) — no dev proxy.
export default defineConfig({
    plugins: [react()],
    server: { port: 5173 },
});
