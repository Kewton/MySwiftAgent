import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Candidate Selection UI
 *
 * Tests the candidate selection flow including:
 * - Candidate card display
 * - Selection interaction
 * - Confirmation flow
 */

test.describe('Candidate Selection', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/mlops/chat');
	});

	test('should display candidate selector with candidates', async ({ page }) => {
		const selector = page.getByTestId('candidate-selector');
		await expect(selector).toBeVisible();

		// Should show multiple candidates
		const candidateCards = page.locator('[data-testid^="candidate-card-"]');
		await expect(candidateCards).toHaveCount(2);
	});

	test('should display candidate card with all required elements', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');
		await expect(cardA).toBeVisible();

		// Check for candidate label (the round badge with letter A)
		await expect(cardA.locator('.rounded-full:has-text("A")')).toBeVisible();

		// Check for description (contains "Sales data analysis")
		await expect(cardA.locator('text=/Sales data analysis/')).toBeVisible();

		// Check for confidence indicator (85%)
		await expect(cardA.locator('text=/85%/')).toBeVisible();

		// Check for requirements preview
		await expect(cardA.locator('text=Data Source')).toBeVisible();
	});

	test('should select candidate on click', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');
		const cardB = page.getByTestId('candidate-card-B');

		// Click to select card A using force to ensure click happens
		await cardA.click({ force: true });
		// Use polling to wait for attribute change
		await expect(async () => {
			const pressed = await cardA.getAttribute('aria-pressed');
			expect(pressed).toBe('true');
		}).toPass({ timeout: 3000 });

		// Select different candidate
		await cardB.click({ force: true });
		await expect(async () => {
			const pressedB = await cardB.getAttribute('aria-pressed');
			expect(pressedB).toBe('true');
		}).toPass({ timeout: 3000 });
	});

	test('should enable confirm button when candidate selected', async ({ page }) => {
		const confirmButton = page.getByTestId('confirm-selection-button');

		// Initially disabled
		await expect(confirmButton).toBeDisabled();

		// Select a candidate
		const cardA = page.getByTestId('candidate-card-A');
		await cardA.click();

		// Wait for selection to update
		await expect(cardA).toHaveAttribute('aria-pressed', 'true', { timeout: 2000 });

		// Confirm button should be enabled
		await expect(confirmButton).toBeEnabled();
	});

	test('should support keyboard navigation', async ({ page }) => {
		const selector = page.getByTestId('candidate-selector');
		const cardA = page.getByTestId('candidate-card-A');

		// Click to select first
		await cardA.click();
		await expect(cardA).toHaveAttribute('aria-pressed', 'true', { timeout: 2000 });

		// Focus the selector and use arrow key
		await selector.focus();
		await page.keyboard.press('ArrowDown');

		// Wait for selection to change
		const cardB = page.getByTestId('candidate-card-B');
		await expect(cardB).toHaveAttribute('aria-pressed', 'true', { timeout: 2000 });
	});

	test('should have proper ARIA attributes for accessibility', async ({ page }) => {
		const selector = page.getByTestId('candidate-selector');

		// The selector itself has role="listbox"
		await expect(selector).toHaveAttribute('role', 'listbox');

		// Check option roles (inside the selector)
		const options = selector.locator('[role="option"]');
		await expect(options).toHaveCount(2);

		// Click to select and check aria-selected changes
		const cardA = page.getByTestId('candidate-card-A');
		await cardA.click();
		await expect(cardA).toHaveAttribute('aria-pressed', 'true', { timeout: 2000 });

		// The option wrapper should have aria-selected
		const optionA = selector.locator('[role="option"]').first();
		await expect(optionA).toHaveAttribute('aria-selected', 'true', { timeout: 2000 });
	});

	test('should show completeness progress bar', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');

		// Check for progress bar
		const progressBar = cardA.locator('[role="progressbar"]');
		await expect(progressBar).toBeVisible();
		await expect(progressBar).toHaveAttribute('aria-valuenow', '75');
	});

	test('should show selected indicator after selection', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');
		await cardA.click();

		// Verify aria-pressed is true
		await expect(cardA).toHaveAttribute('aria-pressed', 'true', { timeout: 2000 });

		// Check for selected indicator (check icon visible when selected)
		// The component shows a checkmark icon when selected
		const selectedIndicator = cardA.locator('svg');
		await expect(selectedIndicator).toBeVisible({ timeout: 2000 });
	});
});
