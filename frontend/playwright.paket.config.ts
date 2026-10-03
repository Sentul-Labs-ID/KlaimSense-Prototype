import { defineConfig } from "@playwright/test";

// Pengemasan proposal (fase 7): tangkapan layar dan video demo 1920x1080 ke assets/.
// Dijalankan lewat `make tangkapan-layar` dan `make rekam-demo` (dataset demo di-reset dulu).
export default defineConfig({
  testDir: "./paket",
  timeout: 300_000,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: process.env.DASHBOARD_URL ?? "http://localhost:3000",
    viewport: { width: 1920, height: 1080 },
    locale: "id-ID",
    timezoneId: "Asia/Jakarta",
  },
});
