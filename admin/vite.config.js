import { defineConfig } from "vite";

const API_TARGET = "http://localhost:8000";
const IGNORED_WARNING_CODE = "MODULE_LEVEL_DIRECTIVE";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  server: {
    proxy: { "/api": API_TARGET },
  },
  build: {
    rollupOptions: {
      // React libraries ship "use client" markers that mean nothing in a plain SPA bundle.
      onwarn(warning, warn) {
        if (warning.code !== IGNORED_WARNING_CODE) warn(warning);
      },
    },
  },
});
