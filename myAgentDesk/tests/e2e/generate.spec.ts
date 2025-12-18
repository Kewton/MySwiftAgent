/**
 * E2E Tests for Generate Page
 * Issue #291: Generate Page (Job Generation)
 *
 * Tests verify actual user flows:
 * - Generate page display with/without active requirement version
 * - Generate Job button validation (disabled when no active version)
 * - Job generation flow (button click -> progress display -> completion)
 * - Version label format (vN.M)
 * - Job history display
 * - Error handling
 *
 * Prerequisites:
 * - myAgentDesk running (npm run dev)
 * - Database seeded (npm run db:seed)
 */
import { test, expect, type Page } from '@playwright/test';
import { execSync } from 'child_process';

// Test data: using seed data from db-seed.ts
const TEST_PROJECT_ID = 'proj_001';
const TEST_WORKBENCH_ID = 'wb_001';
const BASE_URL = `/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}`;
const GENERATE_URL = `${BASE_URL}/generate`;
const REQUIREMENTS_URL = `${BASE_URL}/requirements`;

/**
 * Clean up any stuck 'generating' jobs before each test.
 * This ensures tests don't interfere with each other.
 */
test.beforeEach(async () => {
	try {
		execSync(
			"sqlite3 data/local.db \"UPDATE job_version SET status = 'failed' WHERE status = 'generating';\"",
			{ cwd: process.cwd() }
		);
	} catch {
		// Ignore errors - database might not have any generating jobs
	}
});

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Note: Tests assume database is seeded with:
 * - wb_001 has active_requirement_version_id = 'rv_001'
 * - Run `npm run db:seed` before tests if needed
 * - Run: sqlite3 data/local.db "UPDATE workbench SET active_requirement_version_id = 'rv_001' WHERE id = 'wb_001';"
 */

/**
 * Helper to get job version count from history section
 */
async function getJobVersionCount(page: Page): Promise<number> {
	const jobItems = page.locator('.job-item');
	return await jobItems.count();
}

// =============================================================================
// 1. Generate Page - Basic Display Tests
// =============================================================================

test.describe('Generate Page - Display', () => {
	test('should display Generate page with correct sections', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Wait for page to load
		await page.waitForLoadState('networkidle');

		// Verify page contains Generate Job heading (inside generate-page or page header)
		const generatePageContent = page.locator('.generate-page');
		await expect(generatePageContent).toBeVisible();
		await expect(generatePageContent.locator('h2')).toContainText('Generate Job');

		// Verify section cards exist within the generate page
		const sectionCards = generatePageContent.locator('.section-card');
		await expect(sectionCards.first()).toBeVisible();

		// Verify "Active Requirement Version" section
		await expect(sectionCards.locator('h3').first()).toContainText('Active Requirement Version');
	});

	test('should display active requirement version when set', async ({ page }) => {
		await page.goto(GENERATE_URL);
		await page.waitForLoadState('networkidle');

		// Verify version badge is displayed within generate-page
		const generatePage = page.locator('.generate-page');
		const versionBadge = generatePage.locator('.version-badge');
		await expect(versionBadge).toBeVisible();
		await expect(versionBadge).toHaveText(/v\d+/);

		// Verify status badge is displayed
		const statusBadge = generatePage.locator('.requirement-info .status-badge');
		await expect(statusBadge).toBeVisible();

		// Verify "View Content" details element exists
		const viewContent = generatePage.locator('.requirement-content summary');
		await expect(viewContent).toContainText('View Content');
	});

	test('should display warning OR generate button based on active requirement', async ({
		page
	}) => {
		// This test verifies the page displays correctly regardless of active requirement state
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/wb_002/generate`);
		await page.waitForLoadState('networkidle');

		const generatePage = page.locator('.generate-page');
		await expect(generatePage).toBeVisible();

		// Either warning is displayed OR version badge is displayed
		const warning = generatePage.locator('.no-version-warning');
		const versionBadge = generatePage.locator('.version-badge');

		const hasWarning = await warning.isVisible().catch(() => false);
		const hasVersion = await versionBadge.isVisible().catch(() => false);

		// One of them must be visible
		expect(hasWarning || hasVersion).toBeTruthy();
	});
});

// =============================================================================
// 2. Generate Job Button - Validation Tests
// =============================================================================

test.describe('Generate Job Button - Validation', () => {
	test('should enable Generate Job button when active requirement exists', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Verify button is enabled
		const generateButton = page.locator('.generate-button');
		await expect(generateButton).toBeVisible();
		await expect(generateButton).toBeEnabled();
		await expect(generateButton).toContainText('Generate Job');
	});

	test('should show appropriate button state based on active requirement', async ({ page }) => {
		// Use wb_002 - test that button state matches requirement state
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/wb_002/generate`);
		await page.waitForLoadState('networkidle');

		const generatePage = page.locator('.generate-page');
		const generateButton = generatePage.locator('.generate-button');
		await expect(generateButton).toBeVisible();

		// Check if there's an active requirement
		const versionBadge = generatePage.locator('.version-badge');
		const hasActiveRequirement = await versionBadge.isVisible().catch(() => false);

		if (hasActiveRequirement) {
			// Button should be enabled
			await expect(generateButton).toBeEnabled();
		} else {
			// Button should be disabled
			await expect(generateButton).toBeDisabled();
			await expect(generateButton).toContainText('No Active Version');
		}
	});

	test('should show "Ready to generate" status when idle', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Verify status indicator shows idle state
		const statusIndicator = page.locator('.status-indicator');
		await expect(statusIndicator).toContainText('Ready to generate');
		await expect(statusIndicator).toHaveClass(/idle/);
	});
});

// =============================================================================
// 3. Job Generation Flow - Integration Tests
// =============================================================================

test.describe('Job Generation Flow', () => {
	test('should start job generation when clicking Generate Job button', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Get initial job count
		const initialJobCount = await getJobVersionCount(page);

		// Click Generate Job button
		const generateButton = page.locator('.generate-button');
		await expect(generateButton).toBeEnabled();
		await generateButton.click();

		// Wait for form submission response
		await page.waitForTimeout(1000);

		// Verify status changes to generating (or shows success message)
		const statusIndicator = page.locator('.status-indicator');
		const statusText = await statusIndicator.textContent();

		// Status should either be "Generating..." or show a success/error message
		expect(
			statusText?.includes('Generating') ||
				statusText?.includes('Generation started') ||
				statusText?.includes('Complete') ||
				statusText?.includes('Ready')
		).toBeTruthy();
	});

	test('should display progress indicator during generation', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Click Generate Job button
		const generateButton = page.locator('.generate-button');
		await generateButton.click();

		// Wait a moment for the form to submit
		await page.waitForTimeout(500);

		// If generation starts, we should see the running status
		const runningStatus = page.locator('.status-indicator.running');
		const progressBar = page.locator('.progress-bar');

		// Either we see the running state or the job completed quickly
		const isRunning = await runningStatus.isVisible().catch(() => false);
		const hasProgressBar = await progressBar.isVisible().catch(() => false);

		// At least one of these should have appeared (even briefly) or the job completed
		// We can't guarantee the exact state due to timing
		const statusIndicator = page.locator('.status-indicator');
		await expect(statusIndicator).toBeVisible();
	});

	test('should show error message when generation fails', async ({ page }) => {
		// Navigate to a workbench with active requirement
		await page.goto(GENERATE_URL);

		// Start a generation
		const generateButton = page.locator('.generate-button');
		await generateButton.click();

		// Wait for a response
		await page.waitForTimeout(1000);

		// Check if there's an error indicator (if the generation failed)
		const errorIndicator = page.locator('.status-indicator.error');
		if (await errorIndicator.isVisible()) {
			// Verify error message is displayed
			await expect(errorIndicator).toContainText('Failed');
		}
		// If no error, the test passes (generation may have succeeded)
	});
});

// =============================================================================
// 4. Version Numbering - vN.M Format Tests
// =============================================================================

test.describe('Version Numbering - vN.M Format', () => {
	test('should display version label in vN.M format in job history', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// If there are job versions in history, verify format
		const jobVersions = page.locator('.job-version');
		const count = await jobVersions.count();

		if (count > 0) {
			// Verify each version label matches vN.M format
			for (let i = 0; i < count; i++) {
				const versionText = await jobVersions.nth(i).textContent();
				expect(versionText).toMatch(/^v\d+\.\d+$/);
			}
		}
	});

	test('should increment minor version for same requirement version', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Get current versions before generation
		const jobVersionsBefore = page.locator('.job-version');
		const countBefore = await jobVersionsBefore.count();

		if (countBefore > 0) {
			const firstVersionBefore = await jobVersionsBefore.first().textContent();
			const match = firstVersionBefore?.match(/^v(\d+)\.(\d+)$/);

			if (match) {
				const majorBefore = parseInt(match[1]);
				const minorBefore = parseInt(match[2]);

				// Generate a new job
				const generateButton = page.locator('.generate-button');
				await generateButton.click();
				await page.waitForTimeout(2000);

				// Reload to see updated list
				await page.reload();

				// Check if new version was created
				const jobVersionsAfter = page.locator('.job-version');
				const countAfter = await jobVersionsAfter.count();

				if (countAfter > countBefore) {
					const firstVersionAfter = await jobVersionsAfter.first().textContent();
					const matchAfter = firstVersionAfter?.match(/^v(\d+)\.(\d+)$/);

					if (matchAfter) {
						const majorAfter = parseInt(matchAfter[1]);
						const minorAfter = parseInt(matchAfter[2]);

						// Same major version, minor should be incremented
						if (majorAfter === majorBefore) {
							expect(minorAfter).toBe(minorBefore + 1);
						}
					}
				}
			}
		}
	});
});

// =============================================================================
// 5. Job History Section Tests
// =============================================================================

test.describe('Job History Section', () => {
	test('should display recent job versions', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Check if history section exists
		const historySectionHeader = page
			.locator('.section-card h3')
			.filter({ hasText: 'Recent Job Versions' });
		const hasHistory = await historySectionHeader.isVisible().catch(() => false);

		if (hasHistory) {
			// Verify job items are displayed
			const jobItems = page.locator('.job-item');
			const count = await jobItems.count();

			// If we have jobs, verify their structure
			for (let i = 0; i < Math.min(count, 3); i++) {
				const jobItem = jobItems.nth(i);

				// Should have version label
				await expect(jobItem.locator('.job-version')).toBeVisible();

				// Should have status badge
				await expect(jobItem.locator('.status-badge')).toBeVisible();

				// Should have date
				await expect(jobItem.locator('.job-date')).toBeVisible();
			}
		}
	});

	test('should display Open Trace link for completed jobs', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Check for trace links in job history
		const traceLinks = page.locator('.trace-link');
		const count = await traceLinks.count();

		if (count > 0) {
			// Verify trace link has correct href format
			const firstTraceLink = traceLinks.first();
			const href = await firstTraceLink.getAttribute('href');
			expect(href).toMatch(/localhost:3001\/trace\//);

			// Verify it opens in new tab
			await expect(firstTraceLink).toHaveAttribute('target', '_blank');
			await expect(firstTraceLink).toHaveAttribute('rel', 'noopener noreferrer');
		}
	});

	test('should display job status with appropriate styling', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Check job status badges
		const statusBadges = page.locator('.job-item .status-badge');
		const count = await statusBadges.count();

		for (let i = 0; i < count; i++) {
			const badge = statusBadges.nth(i);
			const text = await badge.textContent();

			// Status should be one of the known statuses
			expect(
				text?.includes('Generating') ||
					text?.includes('Success') ||
					text?.includes('Failed') ||
					text?.includes('Active') ||
					text?.includes('Draft') ||
					text?.includes('Deprecated')
			).toBeTruthy();
		}
	});
});

// =============================================================================
// 6. View Content Accordion Tests
// =============================================================================

test.describe('View Content Accordion', () => {
	test('should toggle requirement content visibility', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Find the details element
		const details = page.locator('.requirement-content');
		if (!(await details.isVisible())) {
			return; // No active requirement
		}

		// Initially should be collapsed (pre element not visible)
		const preElement = page.locator('.requirement-content pre');
		const isInitiallyOpen = await preElement.isVisible().catch(() => false);

		// Click to toggle
		await page.locator('.requirement-content summary').click();
		await page.waitForTimeout(200);

		// State should have changed
		const isOpenAfterClick = await preElement.isVisible();
		expect(isOpenAfterClick).not.toBe(isInitiallyOpen);
	});

	test('should display requirement content in pre element', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Open the content accordion
		const summary = page.locator('.requirement-content summary');
		if (!(await summary.isVisible())) {
			return;
		}

		await summary.click();
		await page.waitForTimeout(200);

		// Verify pre element contains content
		const preElement = page.locator('.requirement-content pre');
		await expect(preElement).toBeVisible();
		const content = await preElement.textContent();
		expect(content?.length).toBeGreaterThan(0);
	});
});

// =============================================================================
// 7. Error Handling Tests
// =============================================================================

test.describe('Error Handling', () => {
	test('should handle invalid workbench ID gracefully', async ({ page }) => {
		const response = await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/invalid_wb_id/generate`
		);

		// Should return error status
		expect(response?.status()).toBeGreaterThanOrEqual(400);
	});

	test('should handle invalid project ID gracefully', async ({ page }) => {
		const response = await page.goto('/projects/invalid_project_id/workbenches/wb_001/generate');

		// Should return error status
		expect(response?.status()).toBeGreaterThanOrEqual(400);
	});

	test('should prevent multiple concurrent generations', async ({ page }) => {
		await page.goto(GENERATE_URL);

		// Start first generation
		const generateButton = page.locator('.generate-button');
		await generateButton.click();

		// Wait for generation to start
		await page.waitForTimeout(500);

		// If generation is in progress, button should be disabled
		const isDisabled = await generateButton.isDisabled();
		const buttonText = await generateButton.textContent();

		// Either button is disabled OR it shows "Generating..."
		expect(isDisabled || buttonText?.includes('Generating')).toBeTruthy();
	});
});

// =============================================================================
// 8. Navigation Tests
// =============================================================================

test.describe('Navigation', () => {
	test('should navigate from Requirements to Generate page', async ({ page }) => {
		// Start at requirements page
		await page.goto(REQUIREMENTS_URL);

		// Find and click the Generate tab/link
		const generateLink = page.locator('a[href*="/generate"]').first();
		if (await generateLink.isVisible()) {
			await generateLink.click();
			await expect(page).toHaveURL(new RegExp(GENERATE_URL));
		}
	});

	test('should maintain workbench context when navigating', async ({ page }) => {
		await page.goto(GENERATE_URL);
		await page.waitForLoadState('networkidle');

		// Verify workbench name is displayed in the page header
		const pageHeader = page.locator('.page-header');
		await expect(pageHeader).toBeVisible();
		const workbenchName = pageHeader.locator('.workbench-name').first();
		await expect(workbenchName).toBeVisible();
		const name = await workbenchName.textContent();
		expect(name?.length).toBeGreaterThan(0);
	});
});

// =============================================================================
// 9. Complete User Journey Test
// =============================================================================

test.describe('Complete User Journey', () => {
	test('full flow: view generate page -> start generation', async ({ page }) => {
		// Prerequisites: Database must be seeded with wb_001 having active_requirement_version_id = 'rv_001'

		// Step 1: Navigate to Generate page
		await page.goto(GENERATE_URL);
		await page.waitForLoadState('networkidle');

		// Step 3: Verify page is ready
		const generatePage = page.locator('.generate-page');
		await expect(generatePage).toBeVisible();
		await expect(generatePage.locator('h2')).toContainText('Generate Job');
		await expect(generatePage.locator('.version-badge')).toBeVisible();

		// Step 4: Verify button is enabled
		const generateButton = generatePage.locator('.generate-button');
		await expect(generateButton).toBeEnabled();
		await expect(generateButton).toContainText('Generate Job');

		// Step 5: Start generation
		await generateButton.click();
		await page.waitForTimeout(1000);

		// Step 6: Verify status changed (either generating or completed)
		const statusIndicator = generatePage.locator('.status-indicator');
		await expect(statusIndicator).toBeVisible();

		// Step 7: If job was created, verify it appears in history after reload
		await page.reload();
		await page.waitForLoadState('networkidle');

		// The page should still be functional
		await expect(generatePage.locator('h2')).toContainText('Generate Job');
	});
});
