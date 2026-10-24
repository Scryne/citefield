import { defineConfig } from '@playwright/test'

const PORT = 8497

// The built UI (npm run build) is served by the real Python app with a fake model (tests/e2e_server.py).
export default defineConfig({
  testDir: 'e2e',
  // one app, one seeded receipt: the files share it and run in order (app.spec before review.spec)
  workers: 1,
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    // locally the installed Edge, no browser download; CI installs Chromium
    channel: process.env.CI ? undefined : 'msedge',
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
    command: `uv run python tests/e2e_server.py ${PORT}`,
    cwd: '..',
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
  },
})
