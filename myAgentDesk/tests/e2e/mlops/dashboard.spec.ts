import { test, expect } from '@playwright/test';

/**
 * E2E Tests for MLOps Dashboard
 *
 * Tests the dashboard display including:
 * - Metrics cards
 * - Real-time chart
 * - Connection status
 * - Navigation
 */

test.describe('MLOps Dashboard', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/mlops');
	});

	test('should display dashboard page with header', async ({ page }) => {
		const dashboard = page.getByTestId('mlops-dashboard');
		await expect(dashboard).toBeVisible();

		await expect(page.locator('h1:has-text("MLOps Dashboard")')).toBeVisible();
	});

	test('should display connection status indicator', async ({ page }) => {
		const status = page.getByTestId('connection-status');
		await expect(status).toBeVisible();

		// Should show either "Live" or "Offline"
		await expect(status.locator('text=/Live|Offline/')).toBeVisible();
	});

	test('should display metrics cards', async ({ page }) => {
		// Check for all metrics cards
		await expect(page.getByTestId('metrics-card-average-score')).toBeVisible();
		await expect(page.getByTestId('metrics-card-total-turns')).toBeVisible();
		await expect(page.getByTestId('metrics-card-success-rate')).toBeVisible();
		await expect(page.getByTestId('metrics-card-avg-latency')).toBeVisible();
		await expect(page.getByTestId('metrics-card-total-sessions')).toBeVisible();
		await expect(page.getByTestId('metrics-card-completion-rate')).toBeVisible();
	});

	test('should display realtime chart', async ({ page }) => {
		const chart = page.getByTestId('realtime-chart');
		await expect(chart).toBeVisible();

		await expect(chart.locator('text=Model Usage Distribution')).toBeVisible();
	});

	test('should show loading state initially', async ({ page }) => {
		// Loading indicators might appear briefly
		// This test checks that the dashboard handles loading state
		await page.goto('/mlops');
		await expect(page.getByTestId('mlops-dashboard')).toBeVisible();
	});

	test('should navigate to other pages via sidebar', async ({ page }) => {
		// Chat page
		await page.getByTestId('nav-chat').click();
		await expect(page).toHaveURL('/mlops/chat');
		await expect(page.getByTestId('mlops-chat-page')).toBeVisible();

		// Diagnostics page
		await page.getByTestId('nav-diagnostics').click();
		await expect(page).toHaveURL('/mlops/diagnostics');
		await expect(page.getByTestId('mlops-diagnostics-page')).toBeVisible();

		// Prompts page
		await page.getByTestId('nav-prompts').click();
		await expect(page).toHaveURL('/mlops/prompts');
		await expect(page.getByTestId('mlops-prompts-page')).toBeVisible();

		// Back to dashboard
		await page.getByTestId('nav-dashboard').click();
		await expect(page).toHaveURL('/mlops');
		await expect(page.getByTestId('mlops-dashboard')).toBeVisible();
	});

	test('should highlight active navigation item', async ({ page }) => {
		const dashboardNav = page.getByTestId('nav-dashboard');
		await expect(dashboardNav).toHaveAttribute('aria-current', 'page');

		await page.getByTestId('nav-chat').click();
		await expect(page.getByTestId('nav-chat')).toHaveAttribute('aria-current', 'page');
		await expect(dashboardNav).not.toHaveAttribute('aria-current', 'page');
	});

	test('should display metrics with proper formatting', async ({ page }) => {
		const avgScoreCard = page.getByTestId('metrics-card-average-score');

		// Should show percentage format (e.g., "78.5%")
		await expect(avgScoreCard.locator('text=/%/')).toBeVisible({ timeout: 10000 });
	});

	test('should have responsive layout', async ({ page }) => {
		// Desktop view
		await page.setViewportSize({ width: 1280, height: 720 });
		await expect(page.locator('aside')).toBeVisible();

		// Mobile view
		await page.setViewportSize({ width: 375, height: 667 });
		await expect(page.locator('aside')).not.toBeVisible();

		// Mobile navigation should be visible
		await expect(page.locator('nav.flex.justify-around')).toBeVisible();
	});
});

test.describe('MLOps Dashboard - Diagnostics Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/mlops/diagnostics');
	});

	test('should display diagnostics page', async ({ page }) => {
		await expect(page.getByTestId('mlops-diagnostics-page')).toBeVisible();
		await expect(page.locator('h1:has-text("Conversation Diagnostics")')).toBeVisible();
	});

	test('should display filter inputs', async ({ page }) => {
		await expect(page.getByTestId('filter-job-id')).toBeVisible();
		await expect(page.getByTestId('filter-user-id')).toBeVisible();
		await expect(page.getByTestId('apply-filter-button')).toBeVisible();
	});

	test('should display diagnostics list', async ({ page }) => {
		// Wait for list to load (demo data)
		await page.waitForSelector('[data-testid^="diagnostic-item-"]', { timeout: 10000 });

		const items = page.locator('[data-testid^="diagnostic-item-"]');
		expect(await items.count()).toBeGreaterThan(0);
	});

	test('should show detail view when selecting item', async ({ page }) => {
		await page.waitForSelector('[data-testid^="diagnostic-item-"]', { timeout: 10000 });

		// Click first item
		await page.locator('[data-testid^="diagnostic-item-"]').first().click();

		// Timeline should be visible
		await expect(page.getByTestId('conversation-timeline')).toBeVisible();
	});

	test('should display conversation timeline with messages', async ({ page }) => {
		await page.waitForSelector('[data-testid^="diagnostic-item-"]', { timeout: 10000 });
		await page.locator('[data-testid^="diagnostic-item-"]').first().click();

		// Check for user and assistant messages
		await expect(page.getByTestId('message-user')).toBeVisible();
		await expect(page.getByTestId('message-assistant')).toBeVisible();
	});
});

test.describe('MLOps Dashboard - Prompts Page', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/mlops/prompts');
	});

	test('should display prompts page', async ({ page }) => {
		await expect(page.getByTestId('mlops-prompts-page')).toBeVisible();
		await expect(page.locator('h1:has-text("Prompt Management")')).toBeVisible();
	});

	test('should display prompt templates list', async ({ page }) => {
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });

		const items = page.locator('[data-testid^="prompt-item-"]');
		expect(await items.count()).toBeGreaterThan(0);
	});

	test('should show version list when selecting prompt', async ({ page }) => {
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });
		await page.locator('[data-testid^="prompt-item-"]').first().click();

		await expect(page.getByTestId('prompt-version-list')).toBeVisible();
	});

	test('should show prompt viewer when selecting version', async ({ page }) => {
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });
		await page.locator('[data-testid^="prompt-item-"]').first().click();

		await page.waitForSelector('[data-testid^="version-"]', { timeout: 10000 });
		await page.locator('[data-testid^="version-"]').first().click();

		await expect(page.getByTestId('prompt-viewer')).toBeVisible();
	});

	test('should copy prompt content to clipboard', async ({ page }) => {
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });
		await page.locator('[data-testid^="prompt-item-"]').first().click();

		await page.waitForSelector('[data-testid^="version-"]', { timeout: 10000 });
		await page.locator('[data-testid^="version-"]').first().click();

		await page.getByTestId('copy-button').click();

		// Should show "Copied!" text
		await expect(page.locator('text=Copied!')).toBeVisible();
	});

	test('should open editor when clicking create new version', async ({ page }) => {
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });
		await page.locator('[data-testid^="prompt-item-"]').first().click();

		await page.waitForSelector('[data-testid^="version-"]', { timeout: 10000 });
		await page.locator('[data-testid^="version-"]').first().click();

		await page.getByTestId('edit-button').click();

		await expect(page.getByTestId('prompt-editor')).toBeVisible();
		await expect(page.getByTestId('content-textarea')).toBeVisible();
	});
});
