import { test, expect } from '@playwright/test';

/**
 * MVP4-D smoke tests.
 * All four tests pass with an empty data directory (no banks, no sessions).
 * Requires both servers running — see playwright.config.ts for instructions.
 */

test('dashboard loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('nav')).toContainText('Gonghaebun');
  await expect(page.locator('h1')).toContainText('Dashboard');
});

test('bank page renders empty state or list', async ({ page }) => {
  await page.goto('/bank');
  await expect(
    page.locator('.concept-list, .empty-state')
  ).toBeVisible({ timeout: 5000 });
});

test('sessions page renders empty state or list', async ({ page }) => {
  await page.goto('/sessions');
  await expect(
    page.locator('table, .empty-state')
  ).toBeVisible({ timeout: 5000 });
});

test('recall page renders heading and bank state', async ({ page }) => {
  await page.goto('/recall');
  await expect(page.locator('h1')).toContainText('Recall Session');
  await expect(
    page.locator('.concept-list, .empty-state')
  ).toBeVisible({ timeout: 5000 });
});

test('recall page accepts concept query param', async ({ page }) => {
  await page.goto('/recall?concept=compactness');
  await expect(page.locator('h1')).toContainText('Recall Session');
  await expect(
    page.locator('.concept-list, .empty-state, .question-card')
  ).toBeVisible({ timeout: 5000 });
});
