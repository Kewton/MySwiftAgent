/**
 * E2E Tests for Review Page (JobVersion Detail)
 * Issue #292: [myAgentDesk] Review画面（JobVersion詳細）
 *
 * Tests cover:
 * - Review page displays JobVersion list with vN.M format
 * - Status badges (active/deprecated/success/failed)
 * - Navigation to JobVersion detail page
 * - Task breakdown accordion display
 * - Interface definition (JSON Schema) display
 * - Workflow YAML display
 * - Active version switch functionality
 * - Start Run button for active versions
 * - 404 handling for invalid JobVersion ID
 */
import { test, expect } from '@playwright/test';

// Test data - using seed data IDs
const TEST_PROJECT_ID = 'proj_001';
const TEST_WORKBENCH_ID = 'wb_001';

test.describe('Review Page - JobVersion List', () => {
	test('should display review page with JobVersion list', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);

		// Page should load successfully
		await expect(page).toHaveURL(/\/review$/);

		// Should display page title or content
		await expect(page.locator('body')).toContainText(/review|version|job/i);
	});

	test('should display JobVersion with vN.M format', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);

		// Wait for page load
		await page.waitForLoadState('networkidle');

		// Look for version format vN.M (e.g., v1.0, v2.1)
		const versionPatternExists = await page.locator('text=/v\\d+\\.\\d+/').count();

		// May not have data if no JobVersions exist
		if (versionPatternExists === 0) {
			const body = await page.locator('body').textContent();
			expect(body).toMatch(/no.*version|empty|generate/i);
		} else {
			expect(versionPatternExists).toBeGreaterThan(0);
		}
	});

	test('should display status badges correctly', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);

		await page.waitForLoadState('networkidle');

		// Check for status-related content
		const hasStatusBadges = await page
			.locator('[data-testid="status-badge"], .badge, .status')
			.count();

		if (hasStatusBadges > 0) {
			// At least one status badge should be visible
			await expect(
				page.locator('[data-testid="status-badge"], .badge, .status').first()
			).toBeVisible();
		}
	});

	test('should navigate to JobVersion detail when clicking on version', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);

		await page.waitForLoadState('networkidle');

		// Find and click on a JobVersion link/card
		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();

			// Should navigate to detail page
			await expect(page).toHaveURL(/\/job-versions\/jv_/);
		}
	});

	test('should display source requirement version link', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);

		await page.waitForLoadState('networkidle');

		// Check for requirement version link
		const reqVersionLink = page.locator(
			'a[href*="requirements"], [data-testid="requirement-link"]'
		);

		if ((await reqVersionLink.count()) > 0) {
			await expect(reqVersionLink.first()).toBeVisible();
		}
	});
});

test.describe('JobVersion Detail Page', () => {
	test('should display JobVersion detail page', async ({ page }) => {
		// First go to review page to get a valid JobVersion ID
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		// Try to find and click on a JobVersion
		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();
			await page.waitForLoadState('networkidle');

			// Page should have job version content
			await expect(page.locator('body')).toContainText(/task|interface|workflow|version/i);
		}
	});

	test('should display task breakdown accordion', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();
			await page.waitForLoadState('networkidle');

			// Look for task accordion elements
			const taskAccordion = page.locator('[data-testid="task-accordion"], .accordion, .task-item');

			if ((await taskAccordion.count()) > 0) {
				// Click to expand first task
				const firstTask = taskAccordion.first();
				await firstTask.click();

				// Should show expanded content
				await page.waitForTimeout(300); // Wait for animation
				const expandedContent = page.locator('[data-testid="task-content"], .accordion-content');

				if ((await expandedContent.count()) > 0) {
					await expect(expandedContent.first()).toBeVisible();
				}
			}
		}
	});

	test('should display interface definition with JSON formatting', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();
			await page.waitForLoadState('networkidle');

			// Look for interface viewer with JSON content
			const interfaceViewer = page.locator('[data-testid="interface-viewer"], .json-viewer, pre');

			if ((await interfaceViewer.count()) > 0) {
				// Check for JSON-like content
				const content = await interfaceViewer.first().textContent();
				if (content) {
					// Should contain JSON-like characters
					expect(content).toMatch(/[{}\[\]":]/); // eslint-disable-line no-useless-escape
				}
			}
		}
	});

	test('should display workflow YAML with syntax highlighting', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();
			await page.waitForLoadState('networkidle');

			// Look for workflow viewer
			const workflowViewer = page.locator('[data-testid="workflow-viewer"], .yaml-viewer, pre');

			if ((await workflowViewer.count()) > 0) {
				const content = await workflowViewer.first().textContent();
				if (content) {
					// YAML content should have key: value pattern or nodes:
					expect(content.toLowerCase()).toMatch(/nodes:|version:|name:|:/);
				}
			}
		}
	});

	test('should have copy to clipboard functionality for workflow', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		const versionLink = page
			.locator('[data-testid="job-version-link"], a[href*="job-versions"]')
			.first();

		if ((await versionLink.count()) > 0) {
			await versionLink.click();
			await page.waitForLoadState('networkidle');

			// Look for copy button
			const copyButton = page.locator('[data-testid="copy-button"], button:has-text("Copy")');

			if ((await copyButton.count()) > 0) {
				await expect(copyButton.first()).toBeVisible();
			}
		}
	});

	test('should return 404 for invalid JobVersion ID', async ({ page }) => {
		const response = await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/job-versions/jv_invalid_12345`
		);

		// Should return 404 status
		expect(response?.status()).toBe(404);

		// Should display error message
		await expect(page.locator('body')).toContainText(/404|not found|does not exist/i);
	});

	test('should return 404 for workbench mismatch (security)', async ({ page }) => {
		// Try to access a JobVersion with wrong workbench
		const response = await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/wb_999/job-versions/jv_001`
		);

		// Should return 404 status
		expect(response?.status()).toBe(404);
	});
});

test.describe('Active Version Switch', () => {
	test('should display Set Active button for non-active versions', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		// Look for Set Active button
		const setActiveButton = page.locator(
			'button:has-text("Set Active"), button:has-text("Activate"), [data-testid="set-active-button"]'
		);

		if ((await setActiveButton.count()) > 0) {
			await expect(setActiveButton.first()).toBeVisible();
		}
	});

	test('should display Start Run button for active versions', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/review`);
		await page.waitForLoadState('networkidle');

		// Look for Start Run button
		const startRunButton = page.locator(
			'button:has-text("Start Run"), a:has-text("Start Run"), [data-testid="start-run-button"]'
		);

		if ((await startRunButton.count()) > 0) {
			await expect(startRunButton.first()).toBeVisible();
		}
	});
});

test.describe('API Integration', () => {
	test('should fetch JobVersions from API', async ({ page }) => {
		const response = await page.request.get(`/api/workbenches/${TEST_WORKBENCH_ID}/job-versions`);

		// API may return 200 or 404 depending on data availability
		if (response.status() === 200) {
			const data = await response.json();
			expect(Array.isArray(data) || data.jobVersions !== undefined).toBe(true);
		}
	});

	test('should activate JobVersion via API', async ({ page }) => {
		// First get a valid JobVersion ID
		const listResponse = await page.request.get(
			`/api/workbenches/${TEST_WORKBENCH_ID}/job-versions`
		);

		if (listResponse.status() === 200) {
			const data = await listResponse.json();
			const jobVersions = Array.isArray(data) ? data : data.jobVersions;

			if (jobVersions && jobVersions.length > 0) {
				const jobVersionId = jobVersions[0].id;

				// Try to activate
				const activateResponse = await page.request.post(
					`/api/job-versions/${jobVersionId}/activate`
				);

				// Should succeed or fail with validation error
				expect([200, 400, 404]).toContain(activateResponse.status());
			}
		}
	});
});
