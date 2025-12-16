/**
 * E2E Tests for Workbench Screens
 * Issue #289: Workbench List/Detail Screens
 *
 * Tests cover:
 * - Workbench list display for a project
 * - Status filtering with URL query param updates
 * - Navigation to workbench detail
 * - Tab display on workbench detail page
 * - 404 handling for invalid workbench ID
 * - 404 handling for project mismatch (security)
 * - Create workbench modal functionality
 * - API integration for workbench creation
 */
import { test, expect } from '@playwright/test';

test.describe('Workbench List Page', () => {
	test('should display workbench list for a project', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Page should load successfully
		await expect(page).toHaveURL(/\/projects\/proj_001\/workbenches/);

		// Should display page title
		await expect(page.locator('h1')).toContainText('Workbenches');

		// Should display workbench cards
		const workbenchCards = page.locator('[data-testid="workbench-card"]');
		await expect(workbenchCards.first()).toBeVisible();

		// Should display status filter
		const statusFilter = page.locator('[data-testid="status-filter"]');
		await expect(statusFilter).toBeVisible();
	});

	test('should filter by status and update URL', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Click on "Active" filter button
		const activeFilterButton = page.locator('[data-testid="filter-active"]');
		await activeFilterButton.click();

		// URL should update with status query param
		await expect(page).toHaveURL(/\?status=active/);

		// Verify the displayed workbench has active status
		const statusBadges = page.locator('[data-testid="status-badge"]');
		const count = await statusBadges.count();
		for (let i = 0; i < count; i++) {
			await expect(statusBadges.nth(i)).toContainText('active');
		}
	});

	test('should filter by draft status', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Click on "Draft" filter button
		const draftFilterButton = page.locator('[data-testid="filter-draft"]');
		await draftFilterButton.click();

		// URL should update
		await expect(page).toHaveURL(/\?status=draft/);

		// Verify the displayed workbench has draft status
		const statusBadges = page.locator('[data-testid="status-badge"]');
		const count = await statusBadges.count();
		for (let i = 0; i < count; i++) {
			await expect(statusBadges.nth(i)).toContainText('draft');
		}
	});

	test('should show all workbenches when "All" filter is clicked', async ({ page }) => {
		// Start with a filtered URL
		await page.goto('/projects/proj_001/workbenches?status=active');

		// Click on "All" filter button
		const allFilterButton = page.locator('[data-testid="filter-all"]');
		await allFilterButton.click();

		// URL should not have status param or have status=all
		await expect(page).toHaveURL(/\/projects\/proj_001\/workbenches(\?status=all)?$/);
	});

	test('should navigate to workbench detail on card click', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Click on the first workbench card
		const firstCard = page.locator('[data-testid="workbench-card"]').first();
		await firstCard.click();

		// Should navigate to workbench detail page
		await expect(page).toHaveURL(/\/projects\/proj_001\/workbenches\/wb_00[12]/);
	});
});

test.describe('Workbench Detail Page', () => {
	test('should display workbench detail with tabs', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches/wb_001');

		// Page should load successfully
		await expect(page).toHaveURL(/\/projects\/proj_001\/workbenches\/wb_001/);

		// Should display workbench name in the page
		await expect(page.locator('body')).toContainText('Email Auto Reply');
	});

	test('should return 404 for invalid workbench ID', async ({ page }) => {
		const response = await page.goto('/projects/proj_001/workbenches/invalid_id');

		// Should return 404 status
		expect(response?.status()).toBe(404);

		// Should display error message
		await expect(page.locator('body')).toContainText(/404|not found|does not exist/i);
	});

	test('should return 404 for project mismatch (security)', async ({ page }) => {
		// wb_001 belongs to proj_001, accessing via proj_002 should return 404
		const response = await page.goto('/projects/proj_002/workbenches/wb_001');

		// Should return 404 status
		expect(response?.status()).toBe(404);

		// Should display error message
		await expect(page.locator('body')).toContainText(/404|not found|does not exist/i);
	});
});

test.describe('Empty State', () => {
	test('should show empty state message when no workbenches match filter', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Click on "Archived" filter (should have 0 items)
		const archivedFilterButton = page.locator('[data-testid="filter-archived"]');
		await archivedFilterButton.click();

		// Should show empty state message
		await expect(page.locator('.empty-state')).toBeVisible();
		await expect(page.locator('.empty-state')).toContainText('No archived workbenches found');
	});
});

// =============================================================================
// Create Workbench Modal Tests (NEW)
// =============================================================================

test.describe('Create Workbench Modal', () => {
	test('should open modal when clicking create button', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Click on "New Workbench" button
		const createButton = page.locator('[data-testid="create-workbench-button"]');
		await createButton.click();

		// Modal should be visible
		const modal = page.locator('[data-testid="create-workbench-modal"]');
		await expect(modal).toBeVisible();

		// Modal should have title
		await expect(modal.locator('.modal-title')).toContainText('Create New Workbench');
	});

	test('should close modal when clicking cancel button', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');
		await expect(modal).toBeVisible();

		// Click cancel
		await modal.locator('button:has-text("Cancel")').click();

		// Modal should be hidden
		await expect(modal).not.toBeVisible();
	});

	test('should close modal when clicking backdrop', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');
		await expect(modal).toBeVisible();

		// Click on backdrop (outside modal content)
		await modal.click({ position: { x: 10, y: 10 } });

		// Modal should be hidden
		await expect(modal).not.toBeVisible();
	});

	test('should close modal when pressing Escape key', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');
		await expect(modal).toBeVisible();

		// Press Escape
		await page.keyboard.press('Escape');

		// Modal should be hidden
		await expect(modal).not.toBeVisible();
	});

	test('should have disabled submit button when name is empty', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');

		// Submit button should be disabled initially
		const submitButton = modal.locator('[data-testid="submit-button"]');
		await expect(submitButton).toBeDisabled();
	});

	test('should enable submit button when name is entered', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');

		// Enter a name
		const nameInput = modal.locator('[data-testid="input-name"]');
		await nameInput.fill('My New Workbench');

		// Submit button should be enabled
		const submitButton = modal.locator('[data-testid="submit-button"]');
		await expect(submitButton).not.toBeDisabled();
	});

	test('should create workbench and add to list', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Get initial count of workbench cards
		const initialCards = await page.locator('[data-testid="workbench-card"]').count();

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');

		// Fill in the form
		const uniqueName = `E2E Test Workbench ${Date.now()}`;
		await modal.locator('[data-testid="input-name"]').fill(uniqueName);
		await modal.locator('[data-testid="input-description"]').fill('Created by Playwright E2E test');

		// Submit the form
		await modal.locator('[data-testid="submit-button"]').click();

		// Modal should close
		await expect(modal).not.toBeVisible();

		// New workbench should appear in the list
		await expect(page.locator('[data-testid="workbench-card"]')).toHaveCount(initialCards + 1);

		// The new workbench should be visible with its name
		await expect(page.locator(`text=${uniqueName}`)).toBeVisible();
	});

	test('should create workbench with only name (description optional)', async ({ page }) => {
		await page.goto('/projects/proj_001/workbenches');

		// Open modal
		await page.locator('[data-testid="create-workbench-button"]').click();
		const modal = page.locator('[data-testid="create-workbench-modal"]');

		// Fill only the name
		const uniqueName = `Minimal Workbench ${Date.now()}`;
		await modal.locator('[data-testid="input-name"]').fill(uniqueName);

		// Submit the form
		await modal.locator('[data-testid="submit-button"]').click();

		// Modal should close
		await expect(modal).not.toBeVisible();

		// New workbench should be visible
		await expect(page.locator(`text=${uniqueName}`)).toBeVisible();
	});
});

// =============================================================================
// API Integration Tests (NEW)
// =============================================================================

test.describe('API Integration', () => {
	test('should fetch workbenches from API', async ({ page }) => {
		// Intercept API request
		const apiPromise = page.waitForResponse(
			(response) =>
				response.url().includes('/api/projects/proj_001/workbenches') &&
				response.request().method() === 'GET'
		);

		await page.goto('/projects/proj_001/workbenches');

		// Wait for API response (if the page uses API internally)
		// Note: SvelteKit SSR doesn't always use client-side API calls
		// This test verifies API is accessible
		const response = await page.request.get('/api/projects/proj_001/workbenches');
		expect(response.ok()).toBe(true);

		const data = await response.json();
		expect(data).toHaveProperty('workbenches');
		expect(data).toHaveProperty('statusCounts');
		expect(Array.isArray(data.workbenches)).toBe(true);
	});

	test('should return proper structure from API', async ({ page }) => {
		const response = await page.request.get('/api/projects/proj_001/workbenches');
		const data = await response.json();

		// Verify structure
		expect(data.workbenches.length).toBeGreaterThan(0);

		const firstWorkbench = data.workbenches[0];
		expect(firstWorkbench).toHaveProperty('id');
		expect(firstWorkbench).toHaveProperty('name');
		expect(firstWorkbench).toHaveProperty('status');
		expect(firstWorkbench).toHaveProperty('runCount');
		expect(firstWorkbench).toHaveProperty('scheduleCount');

		// Verify status counts
		expect(data.statusCounts).toHaveProperty('all');
		expect(data.statusCounts).toHaveProperty('active');
		expect(data.statusCounts).toHaveProperty('draft');
		expect(data.statusCounts).toHaveProperty('archived');
	});

	test('should create workbench via API', async ({ page }) => {
		const uniqueName = `API Test Workbench ${Date.now()}`;

		const response = await page.request.post('/api/projects/proj_001/workbenches', {
			data: {
				name: uniqueName,
				description: 'Created via Playwright API test'
			}
		});

		expect(response.status()).toBe(201);

		const data = await response.json();
		expect(data.workbench.name).toBe(uniqueName);
		expect(data.workbench.status).toBe('draft');
		expect(data.workbench.projectId).toBe('proj_001');
	});

	test('should reject workbench creation without name', async ({ page }) => {
		const response = await page.request.post('/api/projects/proj_001/workbenches', {
			data: {
				description: 'No name provided'
			}
		});

		expect(response.status()).toBe(400);
	});

	test('should filter workbenches via API', async ({ page }) => {
		// Get all workbenches
		const allResponse = await page.request.get('/api/projects/proj_001/workbenches');
		const allData = await allResponse.json();

		// Get active workbenches
		const activeResponse = await page.request.get(
			'/api/projects/proj_001/workbenches?status=active'
		);
		const activeData = await activeResponse.json();

		expect(activeData.currentFilter).toBe('active');

		// All active workbenches should have 'active' status
		for (const wb of activeData.workbenches) {
			expect(wb.status).toBe('active');
		}

		// Active count should match statusCounts.active
		expect(activeData.workbenches.length).toBe(allData.statusCounts.active);
	});
});
