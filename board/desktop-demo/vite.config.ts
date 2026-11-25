import { fileURLToPath, URL } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import { viteSingleFile } from "vite-plugin-singlefile"

// `--mode standalone` writes one HTML file with scripts, styles, fonts and the
// plugin map inlined, so it opens from file:// without a server or a network.
export default defineConfig(({ mode }) => ({
  base: mode === "standalone" ? "./" : "/",
  plugins: [
    react(),
    tailwindcss(),
    ...(mode === "standalone" ? [viteSingleFile({ outputFileName: "design-router-desktop.html" })] : []),
  ],
  server: {
    fs: {
      allow: [
        fileURLToPath(new URL(".", import.meta.url)),
        fileURLToPath(new URL("../../release/design-router-mapa-fuentes.json", import.meta.url)),
      ],
    },
  },
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
}))
