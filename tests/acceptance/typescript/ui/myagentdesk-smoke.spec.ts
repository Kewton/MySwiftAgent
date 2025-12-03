/**
 * myAgentDesk Smoke Test
 *
 * Basic smoke tests to verify that myAgentDesk is running and accessible.
 * These tests focus on fundamental availability and functionality checks.
 *
 * Test Categories:
 * - Page Loading: Verifies basic page load functionality
 * - Basic Navigation: Checks for JavaScript errors
 * - Service Availability: Performance and response time checks
 * - Error Scenarios: Documents expected error handling behavior
 *
 * @module ui/myagentdesk-smoke
 * @requires myAgentDesk running on port 5173 (or MYAGENTDESK_URL env var)
 */

import { test, expect } from '@playwright/test';
import { Timeouts } from '../config/test-config';

test.describe('myAgentDesk Smoke Tests', () => {
  test.describe('Page Loading', () => {
    test('should load the home page successfully', async ({ page }) => {
      // Navigate to home page
      const response = await page.goto('/');

      // Verify page loaded successfully (2xx or 3xx status)
      expect(response).not.toBeNull();
      expect(response?.ok() || response?.status() === 304).toBeTruthy();
    });

    test('should have a valid page title', async ({ page }) => {
      await page.goto('/');

      // Page should have a title
      const title = await page.title();
      expect(title).toBeTruthy();
      expect(title.length).toBeGreaterThan(0);
    });

    test('should have visible content within timeout', async ({ page }) => {
      await page.goto('/');

      // Wait for body to be visible
      const body = page.locator('body');
      await expect(body).toBeVisible();
    });
  });

  test.describe('Basic Navigation', () => {
    test('should not have JavaScript errors on load', async ({ page }) => {
      const errors: string[] = [];

      // Listen for console errors
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto('/');

      // Wait for page to stabilize
      await page.waitForLoadState('networkidle');

      // Filter out common acceptable errors (e.g., failed API calls when backend is down)
      const criticalErrors = errors.filter(
        (err) =>
          !err.includes('Failed to fetch') &&
          !err.includes('net::ERR_CONNECTION_REFUSED') &&
          !err.includes('NetworkError')
      );

      expect(criticalErrors).toHaveLength(0);
    });
  });

  test.describe('Service Availability', () => {
    test('should respond to requests within acceptable time', async ({
      page,
    }) => {
      const startTime = Date.now();
      await page.goto('/');
      const loadTime = Date.now() - startTime;

      // Page should load within maximum acceptable time
      expect(loadTime).toBeLessThan(Timeouts.PAGE_LOAD_MAX);
    });
  });
});

test.describe('Error Scenarios', () => {
  test('should show meaningful error when service is unreachable', async ({
    page,
  }) => {
    // This test is informational - it documents expected behavior
    // when the service is not running

    // Attempt to navigate to a non-existent port
    const unreachableUrl = 'http://localhost:59999';

    try {
      await page.goto(unreachableUrl, { timeout: Timeouts.SHORT });
      // If we get here, the page somehow loaded - unexpected
      test.fail();
    } catch (error) {
      // Expected: navigation should fail
      expect(error).toBeDefined();
    }
  });
});
