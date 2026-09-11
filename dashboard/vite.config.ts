import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// API_PORT lets two checkouts coexist on one machine (default 8000).
const api = `http://localhost:${process.env.API_PORT ?? "8000"}`;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: Number(process.env.PORT ?? 5173), proxy: { "/api": { target: api, rewrite: (p) => p.replace(/^\/api/, "") } } },
});
