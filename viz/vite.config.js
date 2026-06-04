import { defineConfig } from "vite";

// Base path for GitHub Pages: served at https://<user>.github.io/<repo>/, so assets
// must resolve under "/<repo>/". Overridable via VITE_BASE for other repo names.
const base = process.env.VITE_BASE || "/tapestry/";

export default defineConfig({
  base,
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 1600,
  },
});
