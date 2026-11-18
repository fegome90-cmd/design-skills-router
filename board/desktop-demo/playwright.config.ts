import { defineConfig, devices } from "@playwright/test"

const port = Number(process.env.DESKTOP_TEST_PORT ?? 4183)

export default defineConfig({
  testDir: "./tests",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: `http://127.0.0.1:${port}`,
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: `npm run dev -- --port ${port}`,
    url: `http://127.0.0.1:${port}`,
    reuseExistingServer: false,
  },
})
