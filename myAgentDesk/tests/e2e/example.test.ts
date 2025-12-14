import { test, expect } from '@playwright/test';

test('home page has expected content', async ({ page }) => {
	await page.goto('/');
	await expect(page.locator('body')).toBeVisible();
});
