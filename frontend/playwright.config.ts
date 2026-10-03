import { defineConfig } from "@playwright/test";

// Uji asap terhadap dashboard yang sudah berjalan (`make up`), resolusi layar juri 1920x1080.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.DASHBOARD_URL ?? "http://localhost:3000",
    viewport: { width: 1920, height: 1080 },
    locale: "id-ID",
  },
});
