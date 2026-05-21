import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    cssCodeSplit: false,
    rollupOptions: {
      output: {
        entryFileNames: "assets/widget.js",
        chunkFileNames: "assets/widget.js",
        assetFileNames: "assets/[name][extname]",
        inlineDynamicImports: true
      }
    }
  }
});
