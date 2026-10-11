import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" makes the build work from any folder: a custom domain, GitHub Pages
// (https://USER.github.io/REPO/), Vercel or Netlify.
export default defineConfig({
  plugins: [react()],
  base: "./",
});
