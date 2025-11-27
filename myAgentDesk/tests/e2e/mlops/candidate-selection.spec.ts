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

		// Check for candidate label
		await expect(cardA.locator('text=A')).toBeVisible();

		// Check for description
		await expect(cardA.locator('text=Sales data analysis')).toBeVisible();

		// Check for confidence indicator
		await expect(cardA.locator('text=85%')).toBeVisible();

		// Check for requirements preview
		await expect(cardA.locator('text=Data Source')).toBeVisible();
	});

	test('should select candidate on click', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');
		const cardB = page.getByTestId('candidate-card-B');

		// Initially neither selected
		await expect(cardA).not.toHaveAttribute('aria-pressed', 'true');

		// Click to select
		await cardA.click();
		await expect(cardA).toHaveAttribute('aria-pressed', 'true');

		// Select different candidate
		await cardB.click();
		await expect(cardB).toHaveAttribute('aria-pressed', 'true');
		await expect(cardA).toHaveAttribute('aria-pressed', 'false');
	});

	test('should enable confirm button when candidate selected', async ({ page }) => {
		const confirmButton = page.getByTestId('confirm-selection-button');

		// Initially disabled
		await expect(confirmButton).toBeDisabled();

		// Select a candidate
		await page.getByTestId('candidate-card-A').click();

		// Confirm button should be enabled
		await expect(confirmButton).toBeEnabled();
	});

	test('should support keyboard navigation', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');

		// Focus and select with keyboard
		await cardA.focus();
		await page.keyboard.press('Enter');

		await expect(cardA).toHaveAttribute('aria-pressed', 'true');
	});

	test('should have proper ARIA attributes for accessibility', async ({ page }) => {
		const selector = page.getByTestId('candidate-selector');

		// Check listbox role
		await expect(selector.locator('[role="listbox"]')).toBeVisible();

		// Check option roles
		const options = page.locator('[role="option"]');
		await expect(options).toHaveCount(2);

		// Check aria-selected changes on selection
		await page.getByTestId('candidate-card-A').click();
		const optionA = page.locator('[role="option"]').first();
		await expect(optionA).toHaveAttribute('aria-selected', 'true');
	});

	test('should show completeness progress bar', async ({ page }) => {
		const cardA = page.getByTestId('candidate-card-A');

		// Check for progress bar
		const progressBar = cardA.locator('[role="progressbar"]');
		await expect(progressBar).toBeVisible();
		await expect(progressBar).toHaveAttribute('aria-valuenow', '75');
	});

	test('should show selected indicator after selection', async ({ page }) => {
		await page.getByTestId('candidate-card-A').click();

		// Check for selected indicator
		const selectedText = page.getByTestId('candidate-card-A').locator('text=Selected');
		await expect(selectedText).toBeVisible();
	});
});
