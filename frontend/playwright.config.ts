import { defineConfig, devices } from "@playwright/test";
import path from "path";

export default defineConfig({
  testDir: "tests",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 900 },
  },
  projects: [{ name: "chromium", use: { channel: "chromium" } }],
  outputDir: path.join(__dirname, "test-results"),
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
