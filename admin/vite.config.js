import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";

const DEFAULT_API_TARGET = "http://localhost:8000";
const REPO_ROOT = fileURLToPath(new URL("..", import.meta.url));
const IGNORED_WARNING_CODE = "MODULE_LEVEL_DIRECTIVE";

// loadEnv reads the repository .env, and the shell environment wins over it.
export default defineConfig(({ mode }) => {
  const apiTarget = loadEnv(mode, REPO_ROOT, "").API_PROXY_TARGET || DEFAULT_API_TARGET;
  return {
    esbuild: { jsx: "automatic" },
    server: {
      // "/demo/api" reaches the optional demo app; it simply 404s when the demo is off.
      proxy: { "/api": apiTarget, "/demo/api": apiTarget },
    },
    build: {
      rollupOptions: {
        // React libraries ship "use client" markers that mean nothing in a plain SPA bundle.
        onwarn(warning, warn) {
          if (warning.code !== IGNORED_WARNING_CODE) warn(warning);
        },
      },
    },
  };
});
