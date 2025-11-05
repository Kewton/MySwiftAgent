import { expect, test } from '@playwright/test';

test.describe('Home Page', () => {
	test('should load home page successfully', async ({ page }) => {
		await page.goto('/');

		// Check page title
		await expect(page).toHaveTitle(/myAgentDesk/);

		// Check main heading
		const heading = page.getByRole('heading', { level: 1 });
		await expect(heading).toBeVisible();
	});

	test('should navigate to create_job page', async ({ page }) => {
		await page.goto('/');

		// Click "Create Job" button or link
		const createJobLink = page.getByRole('link', { name: /create.*job/i });
		await createJobLink.click();

		// Verify navigation
		await expect(page).toHaveURL(/\/create_job/);
	});

	test('should navigate to settings page', async ({ page }) => {
		await page.goto('/');

		// Click "Settings" button or link
		const settingsLink = page.getByRole('link', { name: /settings/i });
		if (await settingsLink.isVisible()) {
			await settingsLink.click();

			// Verify navigation
			await expect(page).toHaveURL(/\/settings/);
		}
	});

	test('should display navigation sidebar', async ({ page }) => {
		await page.goto('/');

		// Check if sidebar is visible
		const sidebar = page.locator('[data-testid="sidebar"]').or(page.locator('nav'));
		await expect(sidebar.first()).toBeVisible();
	});
});
