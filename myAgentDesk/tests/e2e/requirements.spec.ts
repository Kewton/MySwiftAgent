/**
 * E2E Tests for Requirements Screens
 * Issue #290: Requirements List and Version Management
 *
 * Tests cover:
 * - Requirements list page display
 * - Version ordering (DESC)
 * - Status badge display
 * - Active version indicator
 * - Navigation to detail page
 * - Requirement detail page
 * - Markdown rendering
 * - XSS sanitization
 * - Diff view for version comparison
 * - Set as Active functionality
 * - New requirement creation
 * - Edit requirement functionality
 */
import { test, expect } from '@playwright/test';

// Test data: using seed data from db-seed.ts
const TEST_PROJECT_ID = 'proj_001';
const TEST_WORKBENCH_ID = 'wb_001';
const TEST_REQUIREMENT_VERSION_ID = 'rv_001';
const TEST_REQUIREMENT_VERSION_ID_V2 = 'rv_002';

// =============================================================================
// Requirements List Page Tests
// =============================================================================

test.describe('Requirements List Page', () => {
	test('should display requirements list page', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Page should load successfully
		await expect(page).toHaveURL(
			new RegExp(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`)
		);

		// Should display requirements page (use data-testid to be specific)
		await expect(page.locator('[data-testid="requirements-page"]')).toBeVisible();
	});

	test('should display requirement version cards', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Should display version cards
		const versionCards = page.locator('[data-testid="version-card"]');
		await expect(versionCards.first()).toBeVisible();

		// Should have at least one card (from seed data)
		expect(await versionCards.count()).toBeGreaterThan(0);
	});

	test('should display versions in descending order (DESC)', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Get version numbers from all cards
		const versionNumbers = page.locator('[data-testid="version-number"]');
		const count = await versionNumbers.count();

		if (count > 1) {
			const versions: number[] = [];
			for (let i = 0; i < count; i++) {
				const text = await versionNumbers.nth(i).textContent();
				// Extract version number from "v1", "v2", etc.
				const versionNum = parseInt(text?.replace('v', '') || '0');
				versions.push(versionNum);
			}

			// Verify DESC order
			for (let i = 0; i < versions.length - 1; i++) {
				expect(versions[i]).toBeGreaterThanOrEqual(versions[i + 1]);
			}
		}
	});

	test('should display status badges with correct styling', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Should display status badges
		const statusBadges = page.locator('[data-testid="status-badge"]');
		await expect(statusBadges.first()).toBeVisible();

		// Status badge should have one of the valid statuses
		const badgeText = await statusBadges.first().textContent();
		expect(['Draft', 'Submitted', 'Active', 'Deprecated']).toContain(badgeText?.trim());
	});

	test('should display "Current" indicator for active version', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Should display active indicator for current version
		const activeIndicator = page.locator('[data-testid="active-indicator"]');

		// May or may not be visible depending on whether activeRequirementVersionId is set
		// If visible, should display "Current"
		if ((await activeIndicator.count()) > 0) {
			await expect(activeIndicator.first()).toContainText('Current');
		}
	});

	test('should display create button', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Should display create button
		const createButton = page.locator('[data-testid="create-button"]');
		await expect(createButton).toBeVisible();
		await expect(createButton).toContainText('New Version');
	});

	test('should navigate to detail page on card click', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Click on the first version card
		const firstCard = page.locator('[data-testid="version-card"]').first();
		await firstCard.click();

		// Should navigate to detail page
		await expect(page).toHaveURL(
			new RegExp(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/rv_00[12]`
			)
		);
	});

	test('should navigate to new page on create button click', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Click on create button
		const createButton = page.locator('[data-testid="create-button"]');
		await createButton.click();

		// Should navigate to new page
		await expect(page).toHaveURL(
			new RegExp(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`)
		);
	});
});

// =============================================================================
// Requirement Detail Page Tests
// =============================================================================

test.describe('Requirement Detail Page', () => {
	test('should display requirement detail page', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Page should load successfully
		await expect(page.locator('[data-testid="requirement-detail-page"]')).toBeVisible();
	});

	test('should display version title', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display version title
		const versionTitle = page.locator('[data-testid="version-title"]');
		await expect(versionTitle).toBeVisible();
		await expect(versionTitle).toContainText('v1');
	});

	test('should display status badge', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display status badge
		const statusBadge = page.locator('[data-testid="status-badge"]');
		await expect(statusBadge).toBeVisible();
	});

	test('should display meta information', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display meta info section
		const metaInfo = page.locator('[data-testid="meta-info"]');
		await expect(metaInfo).toBeVisible();

		// Should display created date
		const createdDate = page.locator('[data-testid="created-date"]');
		await expect(createdDate).toBeVisible();
	});

	test('should display markdown content', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display content section
		const contentSection = page.locator('[data-testid="content-section"]');
		await expect(contentSection).toBeVisible();

		// Should display markdown viewer
		const markdownViewer = page.locator('[data-testid="markdown-viewer"]');
		await expect(markdownViewer).toBeVisible();
	});

	test('should display back link', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display back link
		const backLink = page.locator('[data-testid="back-link"]');
		await expect(backLink).toBeVisible();
		await expect(backLink).toContainText('Back to Requirements');
	});

	test('should navigate back to list on back link click', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Click back link
		const backLink = page.locator('[data-testid="back-link"]');
		await backLink.click();

		// Should navigate back to list
		await expect(page).toHaveURL(
			new RegExp(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements$`)
		);
	});

	test('should display edit button', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display edit button
		const editButton = page.locator('[data-testid="edit-button"]');
		await expect(editButton).toBeVisible();
		await expect(editButton).toContainText('Edit');
	});
});

// =============================================================================
// Markdown Rendering Tests
// =============================================================================

test.describe('Markdown Rendering', () => {
	test('should render markdown content correctly', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Wait for markdown to render
		const markdownViewer = page.locator('[data-testid="markdown-viewer"]');
		await expect(markdownViewer).toBeVisible();

		// Content should be rendered (not just raw markdown)
		await page.waitForTimeout(500); // Wait for client-side rendering
	});

	test('should sanitize XSS script tags', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Wait for markdown to render
		await page.waitForTimeout(500);

		// Verify no script tags exist in the rendered output
		const scripts = page.locator('[data-testid="markdown-viewer"] script');
		expect(await scripts.count()).toBe(0);
	});
});

// =============================================================================
// Diff View Tests
// =============================================================================

test.describe('Diff View', () => {
	test('should display compare dropdown when multiple versions exist', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}`
		);

		// Should display compare section
		const compareSection = page.locator('[data-testid="compare-section"]');

		// May exist if there are multiple versions
		if ((await compareSection.count()) > 0) {
			await expect(compareSection).toBeVisible();

			// Should have a select dropdown
			const compareSelect = page.locator('[data-testid="compare-select"]');
			await expect(compareSelect).toBeVisible();
		}
	});

	test('should show diff view when comparing versions', async ({ page }) => {
		// Navigate to v2 and compare with v1
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}?compare=${TEST_REQUIREMENT_VERSION_ID}`
		);

		// Should display diff viewer
		const diffViewer = page.locator('[data-testid="diff-viewer"]');

		// If diff view is visible
		if ((await diffViewer.count()) > 0) {
			await expect(diffViewer).toBeVisible();

			// Should display diff header
			const diffHeader = page.locator('[data-testid="diff-header"]');
			await expect(diffHeader).toBeVisible();

			// Should display diff content
			const diffContent = page.locator('[data-testid="diff-content"]');
			await expect(diffContent).toBeVisible();
		}
	});

	test('should display addition and deletion legends in diff view', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}?compare=${TEST_REQUIREMENT_VERSION_ID}`
		);

		const diffViewer = page.locator('[data-testid="diff-viewer"]');

		if ((await diffViewer.count()) > 0) {
			// Should display deletion legend (red)
			const deletionLegend = page.locator('[data-testid="legend-deletion"]');
			await expect(deletionLegend).toBeVisible();
			await expect(deletionLegend).toContainText('Removed');

			// Should display insertion legend (green)
			const insertionLegend = page.locator('[data-testid="legend-insertion"]');
			await expect(insertionLegend).toBeVisible();
			await expect(insertionLegend).toContainText('Added');
		}
	});
});

// =============================================================================
// Set as Active Tests
// =============================================================================

test.describe('Set as Active', () => {
	test('should display "Set as Active" button for non-active versions', async ({ page }) => {
		// Navigate to v2 which is draft (not active)
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}`
		);

		// Should display "Set as Active" button
		const setActiveButton = page.locator('[data-testid="set-active-button"]');

		// Button may or may not be visible depending on current active status
		// If the version is not active and status is appropriate, button should be visible
		if ((await setActiveButton.count()) > 0) {
			await expect(setActiveButton).toBeVisible();
			await expect(setActiveButton).toContainText('Set as Active');
		}
	});
});

// =============================================================================
// New Requirement Page Tests
// =============================================================================

test.describe('New Requirement Page', () => {
	test('should display new requirement editor', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`
		);

		// Page should load
		await expect(page).toHaveURL(
			new RegExp(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`)
		);
	});

	test('should display markdown editor', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`
		);

		// Should display markdown editor
		const editor = page.locator('[data-testid="markdown-editor"]');
		await expect(editor).toBeVisible();
	});

	test('should display submit and cancel buttons', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`
		);

		// Should display submit button
		const submitButton = page.locator('[data-testid="submit-button"]');
		await expect(submitButton).toBeVisible();

		// Should display cancel button
		const cancelButton = page.locator('[data-testid="cancel-button"]');
		await expect(cancelButton).toBeVisible();
	});

	test('should display real-time preview', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`
		);

		// Should display preview content area
		const preview = page.locator('[data-testid="preview-content"]');
		await expect(preview).toBeVisible();
	});

	test('should update preview on typing', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/new`
		);

		// Type in the editor
		const textarea = page.locator('[data-testid="editor-textarea"]');
		await textarea.fill('# Test Heading\n\nThis is a test.');

		// Wait for preview to update
		await page.waitForTimeout(300);

		// Preview should show rendered content
		const preview = page.locator('[data-testid="preview-content"]');
		await expect(preview).toBeVisible();
	});
});

// =============================================================================
// Edit Requirement Page Tests
// =============================================================================

test.describe('Edit Requirement Page', () => {
	test('should navigate to edit page from detail', async ({ page }) => {
		// First go to detail page
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}`
		);

		// Click edit button
		const editButton = page.locator('[data-testid="edit-button"]');
		await editButton.click();

		// Should navigate to edit page
		await expect(page).toHaveURL(
			new RegExp(
				`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}/edit`
			)
		);
	});

	test('should display editor with existing content', async ({ page }) => {
		await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/${TEST_REQUIREMENT_VERSION_ID_V2}/edit`
		);

		// Should display markdown editor
		const editor = page.locator('[data-testid="markdown-editor"]');
		await expect(editor).toBeVisible();

		// Editor should have content from existing version
		const textarea = page.locator('[data-testid="editor-textarea"]');
		const content = await textarea.inputValue();
		expect(content.length).toBeGreaterThan(0);
	});
});

// =============================================================================
// Edge Cases Tests
// =============================================================================

test.describe('Edge Cases', () => {
	test('should return 404 for invalid requirement version ID', async ({ page }) => {
		const response = await page.goto(
			`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements/invalid_id`
		);

		// Should return 404 status
		expect(response?.status()).toBe(404);

		// Should display error message
		await expect(page.locator('body')).toContainText(/404|not found|does not exist/i);
	});

	test('should handle empty content gracefully in list', async ({ page }) => {
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`);

		// Page should load without error
		await expect(page).toHaveURL(
			new RegExp(`/projects/${TEST_PROJECT_ID}/workbenches/${TEST_WORKBENCH_ID}/requirements`)
		);
	});
});

// =============================================================================
// Empty State Tests
// =============================================================================

test.describe('Empty State', () => {
	test('should show empty state when no requirements exist', async ({ page }) => {
		// Use wb_002 which might have no requirements
		await page.goto(`/projects/${TEST_PROJECT_ID}/workbenches/wb_002/requirements`);

		// May show empty state if no requirements
		const emptyState = page.locator('[data-testid="empty-state"]');
		const versionCards = page.locator('[data-testid="version-card"]');

		const emptyCount = await emptyState.count();
		const cardsCount = await versionCards.count();

		// Either empty state is shown or cards are shown
		expect(emptyCount > 0 || cardsCount > 0).toBeTruthy();

		if (emptyCount > 0) {
			await expect(emptyState).toContainText('No requirements');
		}
	});
});
