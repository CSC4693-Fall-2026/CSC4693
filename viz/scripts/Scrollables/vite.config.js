import { defineConfig } from "vite";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  publicDir: "scrollable_map/public",
  build: {
    rollupOptions: {
      input: {
        scrollableMap: fileURLToPath(new URL("./scrollable_map/index.html", import.meta.url)),
      },
    },
  },
});
