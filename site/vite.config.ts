import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// GitHub Pages serves the site from a project subpath: /<repo>/.
// In dev/preview we serve from "/" so localhost URLs stay clean; in a
// production build we default to "/formula1/". Override either with
// VITE_BASE (e.g. for a custom deploy path).
export default defineConfig(({ command }) => ({
  plugins: [react(), tailwindcss()],
  base: process.env.VITE_BASE ?? (command === "build" ? "/formula1/" : "/"),
}));
