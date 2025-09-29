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
