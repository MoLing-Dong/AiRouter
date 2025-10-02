import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-react-components/vite";
import Pages from "vite-plugin-pages";
import { fileURLToPath, URL } from "node:url";

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      // 代理 API 请求到后端服务器，解决开发环境跨域问题
      "/api": {
        target: process.env.VITE_API_BASE_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path,
      },
      // 代理管理后台 API 请求
      "/admin": {
        target: process.env.VITE_API_BASE_URL || "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path,
      },
    },
  },
  plugins: [
    react(),
    Pages({
      dirs: "src/pages",
      extensions: ["tsx"],
      resolver: "react",
    }),
    AutoImport({
      imports: ["react"],
      dts: true,
      eslintrc: {
        enabled: true,
        filepath: "./.eslintrc-auto-import.json",
      },
    }),
    Components({
      dts: {
        filename: "src/components.d.ts",
      },
    }),
  ],
});
