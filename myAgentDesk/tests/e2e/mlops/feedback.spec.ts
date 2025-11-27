import { test, expect } from '@playwright/test';

/**
 * E2E Tests for Feedback Form
 *
 * Tests the feedback submission flow including:
 * - Score slider interaction
 * - Form validation
 * - Modal behavior
 */

test.describe('Feedback Form', () => {
	test.beforeEach(async ({ page }) => {
		await page.goto('/mlops/chat');
	});

	test('should open feedback modal on button click', async ({ page }) => {
		const openButton = page.getByTestId('open-feedback-button');
		await openButton.click();

		const modal = page.getByTestId('feedback-modal');
		await expect(modal).toBeVisible();
	});

	test('should display all score sliders', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		// Check all four score sliders
		await expect(page.getByTestId('score-slider-requirement-clarity')).toBeVisible();
		await expect(page.getByTestId('score-slider-interpretation-accuracy')).toBeVisible();
		await expect(page.getByTestId('score-slider-response-helpfulness')).toBeVisible();
		await expect(page.getByTestId('score-slider-overall-satisfaction')).toBeVisible();
	});

	test('should select score values on click', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		const slider = page.getByTestId('score-slider-requirement-clarity');
		const score5 = slider.getByTestId('score-5');

		await score5.click();

		// Check aria-checked attribute
		await expect(score5).toHaveAttribute('aria-checked', 'true');
	});

	test('should enable submit button when at least one score is selected', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		const submitButton = page.getByTestId('feedback-submit');

		// Initially disabled
		await expect(submitButton).toBeDisabled();

		// Select one score
		await page.getByTestId('score-slider-requirement-clarity').getByTestId('score-5').click();

		// Should be enabled now
		await expect(submitButton).toBeEnabled();
	});

	test('should close modal on cancel', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();
		await expect(page.getByTestId('feedback-modal')).toBeVisible();

		await page.getByTestId('feedback-cancel').click();
		await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
	});

	test('should close modal on X button click', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();
		await expect(page.getByTestId('feedback-modal')).toBeVisible();

		await page.getByTestId('close-modal-button').click();
		await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
	});

	test('should close modal on Escape key', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();
		await expect(page.getByTestId('feedback-modal')).toBeVisible();

		await page.keyboard.press('Escape');
		await expect(page.getByTestId('feedback-modal')).not.toBeVisible();
	});

	test('should allow entering comment text', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		const commentBox = page.getByTestId('feedback-comment');
		await commentBox.fill('Great experience!');

		await expect(commentBox).toHaveValue('Great experience!');
	});

	test('should display score labels correctly', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		const slider = page.getByTestId('score-slider-requirement-clarity');

		// Check all score labels exist
		await expect(slider.locator('text=Poor')).toBeVisible();
		await expect(slider.locator('text=Fair')).toBeVisible();
		await expect(slider.locator('text=Good')).toBeVisible();
		await expect(slider.locator('text=Very Good')).toBeVisible();
		await expect(slider.locator('text=Excellent')).toBeVisible();
	});

	test('should have proper ARIA attributes', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		// Modal should have dialog role
		const modal = page.getByTestId('feedback-modal');
		await expect(modal.locator('[role="dialog"]')).toBeVisible();
		await expect(modal.locator('[aria-modal="true"]')).toBeVisible();

		// Score buttons should have radio role
		const scoreButtons = page.locator('[role="radio"]');
		expect(await scoreButtons.count()).toBeGreaterThan(0);
	});

	test('should submit feedback with all scores', async ({ page }) => {
		await page.getByTestId('open-feedback-button').click();

		// Select all scores
		await page.getByTestId('score-slider-requirement-clarity').getByTestId('score-5').click();
		await page.getByTestId('score-slider-interpretation-accuracy').getByTestId('score-4').click();
		await page.getByTestId('score-slider-response-helpfulness').getByTestId('score-5').click();
		await page.getByTestId('score-slider-overall-satisfaction').getByTestId('score-5').click();

		// Add comment
		await page.getByTestId('feedback-comment').fill('Very helpful!');

		// Submit
		await page.getByTestId('feedback-submit').click();

		// Modal should close (assuming API mock or demo mode)
		// In real test, we would mock the API
	});
});
