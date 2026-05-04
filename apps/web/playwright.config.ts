import { defineConfig } from '@playwright/test';

/**
 * Playwright config for MVP4-D smoke tests.
 *
 * Manual preconditions — both servers must be running before npm run test:e2e:
 *
 *   Terminal 1 (repo root):
 *     uvicorn apps.api.main:app --reload
 *
 *   Terminal 2 (apps/web):
 *     npm run dev
 *
 *   Terminal 3 (apps/web):
 *     npm run test:e2e
 */
export default defineConfig({
  testDir: './tests/e2e',
  use: {
    baseURL: 'http://localhost:5173',
  },
  timeout: 15_000,
  retries: 0,
});
