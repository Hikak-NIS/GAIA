import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://localhost:5174",
    channel: "chrome",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command:
        "powershell -NoProfile -ExecutionPolicy Bypass -File ../../scripts/e2e-api.ps1",
      url: "http://127.0.0.1:8001/api/v1/health",
      reuseExistingServer: false,
      env: {
        DATABASE_URL: "sqlite:///D:/GAIA/data/gaia_e2e.db",
        WEB_ORIGIN: "http://localhost:5174",
        BACKGROUND_ENABLED: "true",
      },
    },
    {
      command: "vite --host localhost --port 5174",
      url: "http://localhost:5174",
      reuseExistingServer: false,
      env: { VITE_API_TARGET: "http://127.0.0.1:8001" },
    },
  ],
});
