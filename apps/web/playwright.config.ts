import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests drive the real stack: Vite dev server -> FastAPI -> PostgreSQL
 * -> M4 solver. The API is started by apps/api/scripts/e2e_server.py against a
 * throw-away database (default: thermpro_e2e); it is dropped and recreated each run.
 *
 *   E2E_PYTHON   python interpreter with thermpro-api installed (default: python3)
 *   THERMPRO_DATABASE_URL   database for the e2e API (default: .../thermpro_e2e)
 */
// Resolve relative to apps/web.
const python = process.env.E2E_PYTHON ?? "python3";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} ../api/scripts/e2e_server.py 8000`,
      url: "http://localhost:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      command: "npx vite --port 3000 --strictPort",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
  ],
});
