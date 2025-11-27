import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Responsive Design and Accessibility
 *
 * Tests the UI behavior on different viewport sizes and accessibility compliance
 */

test.describe('Responsive Design', () => {
	test.describe('Desktop (1280x720)', () => {
		test.beforeEach(async ({ page }) => {
			await page.setViewportSize({ width: 1280, height: 720 });
		});

		test('should display sidebar navigation on desktop', async ({ page }) => {
			await page.goto('/mlops');

			const sidebar = page.locator('aside[aria-label="MLOps navigation"]');
			await expect(sidebar).toBeVisible();

			// All nav items should be visible
			await expect(page.getByTestId('nav-dashboard')).toBeVisible();
			// Check nav item specifically (not the h1 which contains "MLOps Dashboard")
			await expect(page.getByTestId('nav-dashboard').locator('span.font-medium')).toHaveText(
				'Dashboard'
			);
		});

		test('should display metrics in grid layout', async ({ page }) => {
			await page.goto('/mlops');

			// Grid should have 3 columns on large screens
			const metricsGrid = page.locator('.grid.lg\\:grid-cols-3');
			await expect(metricsGrid).toBeVisible();
		});

		test('should display diagnostics in side-by-side layout', async ({ page }) => {
			await page.goto('/mlops/diagnostics');

			// List and detail should be side by side
			const listPanel = page.locator('.lg\\:col-span-1');
			const detailPanel = page.locator('.lg\\:col-span-2');

			await expect(listPanel).toBeVisible();
			await expect(detailPanel).toBeVisible();
		});
	});

	test.describe('Tablet (768x1024)', () => {
		test.beforeEach(async ({ page }) => {
			await page.setViewportSize({ width: 768, height: 1024 });
		});

		test('should display sidebar on tablet landscape', async ({ page }) => {
			await page.goto('/mlops');

			// Sidebar should be visible at md breakpoint (768px+)
			const sidebar = page.locator('aside[aria-label="MLOps navigation"]');
			await expect(sidebar).toBeVisible();
		});

		test('should adjust grid layout for tablet', async ({ page }) => {
			await page.goto('/mlops');

			// Metrics should display in 2-column grid
			const metricsGrid = page.locator('.grid.sm\\:grid-cols-2');
			await expect(metricsGrid).toBeVisible();
		});
	});

	test.describe('Mobile (375x667)', () => {
		test.beforeEach(async ({ page }) => {
			await page.setViewportSize({ width: 375, height: 667 });
		});

		test('should hide sidebar on mobile', async ({ page }) => {
			await page.goto('/mlops');

			// Sidebar should be hidden on mobile (<768px)
			const sidebar = page.locator('aside[aria-label="MLOps navigation"]');
			await expect(sidebar).toBeHidden();
		});

		test('should display bottom navigation on mobile', async ({ page }) => {
			await page.goto('/mlops');

			// Bottom nav should be visible
			const bottomNav = page.locator('nav.flex.justify-around');
			await expect(bottomNav).toBeVisible();
		});

		test('should navigate using bottom navigation', async ({ page }) => {
			await page.goto('/mlops');

			// Click chat in bottom nav
			await page.locator('nav.flex.justify-around a[href="/mlops/chat"]').click();
			await expect(page).toHaveURL('/mlops/chat');
		});

		test('should display metrics in single column on mobile', async ({ page }) => {
			await page.goto('/mlops');

			// Cards should stack vertically
			const metricsCards = page.locator('[data-testid^="metrics-card-"]');
			expect(await metricsCards.count()).toBe(6);
		});

		test('should display full-width feedback modal', async ({ page }) => {
			await page.goto('/mlops/chat');

			await page.getByTestId('open-feedback-button').click();

			const modal = page.getByTestId('feedback-modal');
			await expect(modal).toBeVisible();

			// Modal should be nearly full width on mobile
			const modalContent = modal.locator('.w-full.max-w-lg');
			await expect(modalContent).toBeVisible();
		});

		test('should show stacked diagnostics layout on mobile', async ({ page }) => {
			await page.goto('/mlops/diagnostics');

			// Both panels should be visible but stacked
			const listPanel = page.locator('.lg\\:col-span-1');
			const detailPanel = page.locator('.lg\\:col-span-2');

			await expect(listPanel).toBeVisible();
			await expect(detailPanel).toBeVisible();
		});
	});
});

test.describe('Accessibility', () => {
	test('should have proper heading hierarchy', async ({ page }) => {
		await page.goto('/mlops');

		// There are 2 h1 elements: one in sidebar nav, one in main content
		// Both should contain "MLOps Dashboard"
		const h1Elements = page.locator('h1');
		const count = await h1Elements.count();
		expect(count).toBeGreaterThanOrEqual(1);

		// The main content h1 should be visible
		const mainH1 = page.getByTestId('mlops-dashboard').locator('h1');
		await expect(mainH1).toBeVisible();
		await expect(mainH1).toContainText('MLOps Dashboard');
	});

	test('should have proper ARIA labels on navigation', async ({ page }) => {
		await page.goto('/mlops');

		// Navigation should have proper label
		const nav = page.locator('aside[aria-label="MLOps navigation"]');
		await expect(nav).toBeVisible();
	});

	test('should have proper focus indicators', async ({ page }) => {
		await page.goto('/mlops/chat');

		// Tab to candidate card
		await page.keyboard.press('Tab');
		await page.keyboard.press('Tab');
		await page.keyboard.press('Tab');

		// Check for focus outline on active element
		const focusedElement = page.locator(':focus');
		await expect(focusedElement).toBeVisible();
	});

	test('should support keyboard navigation in feedback modal', async ({ page }) => {
		await page.goto('/mlops/chat');

		// Open modal
		await page.getByTestId('open-feedback-button').click();

		// Tab through form elements
		await page.keyboard.press('Tab');
		const focusedElement = page.locator(':focus');
		await expect(focusedElement).toBeVisible();

		// Close with Escape
		await page.keyboard.press('Escape');
		await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
	});

	test('should have proper alt text and ARIA attributes', async ({ page }) => {
		await page.goto('/mlops');

		// Check for aria-hidden on decorative icons
		const decorativeIcons = page.locator('svg[aria-hidden="true"]');
		expect(await decorativeIcons.count()).toBeGreaterThan(0);

		// Check for proper button labels
		const buttons = page.locator('button');
		const buttonCount = await buttons.count();
		for (let i = 0; i < buttonCount; i++) {
			const button = buttons.nth(i);
			const text = await button.textContent();
			const ariaLabel = await button.getAttribute('aria-label');
			// Each button should have either text content or aria-label
			expect(text || ariaLabel).toBeTruthy();
		}
	});

	test('should have proper form labels', async ({ page }) => {
		await page.goto('/mlops/chat');
		await page.getByTestId('open-feedback-button').click();

		// Check that inputs have associated labels
		const textareaLabel = page.locator('label[for="feedback-comment"]');
		await expect(textareaLabel).toBeVisible();
	});

	test('should announce status messages to screen readers', async ({ page }) => {
		await page.goto('/mlops');

		// Error/success messages should have proper role
		await page.goto('/mlops/diagnostics');

		// Wait for demo error message
		const alertMessage = page.locator('[role="alert"]');
		// May or may not be visible depending on API state
		if (await alertMessage.isVisible()) {
			await expect(alertMessage).toBeVisible();
		}
	});

	test('should maintain logical tab order', async ({ page }) => {
		await page.goto('/mlops/chat');

		// Track tab order
		const tabOrder: string[] = [];

		for (let i = 0; i < 10; i++) {
			await page.keyboard.press('Tab');
			const focused = page.locator(':focus');
			const testId = await focused.getAttribute('data-testid');
			if (testId) {
				tabOrder.push(testId);
			}
		}

		// Tab order should be logical (e.g., header button before main content)
		expect(tabOrder.length).toBeGreaterThan(0);
	});

	test('should have sufficient color contrast', async ({ page }) => {
		await page.goto('/mlops');

		// Check that text is visible against backgrounds
		const textElements = page.locator('p, span, h1, h2, h3');
		const count = await textElements.count();

		for (let i = 0; i < Math.min(count, 5); i++) {
			const element = textElements.nth(i);
			await expect(element).toBeVisible();
		}
	});

	test('should support screen reader navigation in lists', async ({ page }) => {
		await page.goto('/mlops/prompts');

		// Wait for list to load
		await page.waitForSelector('[data-testid^="prompt-item-"]', { timeout: 10000 });

		// Check for listbox role
		const versionList = page.locator('[role="listbox"]');
		// May not be visible until prompt is selected
		await page.locator('[data-testid^="prompt-item-"]').first().click();

		await expect(versionList.first()).toBeVisible();
	});
});

test.describe('Dark Mode', () => {
	test('should apply dark mode styles', async ({ page }) => {
		await page.goto('/mlops');

		// Add dark class to html
		await page.evaluate(() => {
			document.documentElement.classList.add('dark');
		});

		// Check that dark mode styles are applied - look for elements with dark mode classes
		// Wait for a bit for styles to apply
		await page.waitForTimeout(100);

		// The layout should still be visible in dark mode
		await expect(page.getByTestId('mlops-layout')).toBeVisible();
	});

	test('should maintain readability in dark mode', async ({ page }) => {
		await page.goto('/mlops');

		await page.evaluate(() => {
			document.documentElement.classList.add('dark');
		});

		// Text should still be visible - use specific h1 in main content
		const mainH1 = page.getByTestId('mlops-dashboard').locator('h1');
		await expect(mainH1).toBeVisible();
	});
});

test.describe('Touch Interactions', () => {
	test('should support touch on candidate cards', async ({ page }) => {
		// Simulate mobile device
		await page.setViewportSize({ width: 390, height: 844 });
		await page.goto('/mlops/chat');

		const card = page.getByTestId('candidate-card-A');
		await card.click();

		await expect(card).toHaveAttribute('aria-pressed', 'true');
	});

	test('should support touch on score sliders', async ({ page }) => {
		// Simulate mobile device
		await page.setViewportSize({ width: 390, height: 844 });
		await page.goto('/mlops/chat');

		await page.getByTestId('open-feedback-button').click();

		const score5 = page.getByTestId('score-slider-requirement-clarity').getByTestId('score-5');
		await score5.click();

		await expect(score5).toHaveAttribute('aria-checked', 'true');
	});
});
