import { test, expect } from '@playwright/test';

test.describe('MLOps Interaction Test on Port 8003', () => {
	test('should verify page interactivity and metrics display', async ({ page }) => {
		// Set longer timeout
		test.setTimeout(60000);

		// Track console errors
		const consoleErrors: string[] = [];
		page.on('console', (msg) => {
			if (msg.type() === 'error') {
				consoleErrors.push(msg.text());
			}
		});

		// Navigate to MLOps Dashboard
		await page.goto('http://localhost:8003/mlops', { waitUntil: 'domcontentloaded' });

		// Wait for initial content to appear
		await page.waitForSelector('text=MLOps Dashboard', { timeout: 10000 });

		// Wait for loading to complete (metrics cards should show values)
		await page.waitForTimeout(2000);

		// Take screenshot of initial state
		await page.screenshot({ path: 'test-results/interaction-01-initial.png' });

		// Verify metrics cards are displayed with values (not just skeleton)
		const metricsCards = page.locator('[data-testid="mlops-dashboard"] .grid > div');
		const cardCount = await metricsCards.count();
		expect(cardCount).toBeGreaterThan(0);

		// Test sidebar navigation - Click on "Chat"
		const chatLink = page.locator('a[href="/mlops/chat"]').first();
		await expect(chatLink).toBeVisible();
		await chatLink.click();
		await page.waitForURL('**/mlops/chat');
		await page.waitForTimeout(1000);
		await page.screenshot({ path: 'test-results/interaction-02-chat.png' });

		// Verify URL changed
		expect(page.url()).toContain('/mlops/chat');

		// Test navigation to Diagnostics
		const diagnosticsLink = page.locator('a[href="/mlops/diagnostics"]').first();
		await expect(diagnosticsLink).toBeVisible();
		await diagnosticsLink.click();
		await page.waitForURL('**/mlops/diagnostics');
		await page.waitForTimeout(1000);
		await page.screenshot({ path: 'test-results/interaction-03-diagnostics.png' });

		// Verify URL changed
		expect(page.url()).toContain('/mlops/diagnostics');

		// Test navigation to Prompts
		const promptsLink = page.locator('a[href="/mlops/prompts"]').first();
		await expect(promptsLink).toBeVisible();
		await promptsLink.click();
		await page.waitForURL('**/mlops/prompts');
		await page.waitForTimeout(1000);
		await page.screenshot({ path: 'test-results/interaction-04-prompts.png' });

		// Verify URL changed
		expect(page.url()).toContain('/mlops/prompts');

		// Go back to Dashboard
		const dashboardLink = page.locator('a[href="/mlops"]').first();
		await dashboardLink.click();
		await page.waitForURL('**/mlops');
		await page.waitForTimeout(1000);
		await page.screenshot({ path: 'test-results/interaction-05-dashboard-return.png' });

		// Log any console errors for debugging
		if (consoleErrors.length > 0) {
			console.log('Console errors:', consoleErrors);
		}
	});

	test('should verify API connectivity', async ({ page }) => {
		// Check if API responds
		const metricsResponse = await page.request.get(
			'http://localhost:8003/aiagent-api/v1/observability/requirement-definition-metrics'
		);
		expect(metricsResponse.ok()).toBe(true);

		const metrics = await metricsResponse.json();
		expect(metrics).toHaveProperty('metrics');
		expect(metrics.metrics).toHaveProperty('average_score');
		expect(metrics.metrics).toHaveProperty('total_sessions');
	});
});
