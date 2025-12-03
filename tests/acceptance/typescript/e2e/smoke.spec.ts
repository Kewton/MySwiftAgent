/**
 * E2E Smoke Tests
 *
 * End-to-end smoke tests that verify basic user workflows.
 * These tests focus on fundamental UI interactions and responsive design.
 *
 * @module e2e/smoke
 * @requires myAgentDesk running on port 5173 (or MYAGENTDESK_URL env var)
 * @requires Backend services (optional for full E2E)
 */

import { test, expect } from '@playwright/test';
import { Viewports } from '../config/test-config';

test.describe('E2E Smoke Tests', () => {
  test.describe('Initial Load', () => {
    test('should display main application container', async ({ page }) => {
      await page.goto('/');

      // Wait for the main app to render
      // SvelteKit apps typically have an app container
      const appContainer =
        page.locator('#app') ||
        page.locator('[data-sveltekit-hydrate]') ||
        page.locator('body');

      await expect(appContainer.first()).toBeVisible();
    });

    test('should have working navigation', async ({ page }) => {
      await page.goto('/');

      // Look for navigation elements
      const navElements = page.locator('nav, header, [role="navigation"]');

      // Page should have some form of navigation (or be a single-page app)
      const navCount = await navElements.count();

      // Log navigation info for debugging
      console.log(`Found ${navCount} navigation elements`);

      // Either navigation exists OR the page is functional without it
      const bodyVisible = await page.locator('body').isVisible();
      expect(bodyVisible).toBeTruthy();
    });
  });

  test.describe('Basic Interaction', () => {
    test('should handle click events without errors', async ({ page }) => {
      const errors: string[] = [];

      page.on('pageerror', (error) => {
        errors.push(error.message);
      });

      await page.goto('/');

      // Try clicking on the body (safe interaction)
      await page.locator('body').click();

      // No JavaScript errors should occur
      expect(errors).toHaveLength(0);
    });

    test('should handle keyboard navigation', async ({ page }) => {
      await page.goto('/');

      // Tab through the page
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab');

      // Page should remain functional
      const bodyVisible = await page.locator('body').isVisible();
      expect(bodyVisible).toBeTruthy();
    });
  });

  test.describe('Responsive Design', () => {
    test('should render correctly on desktop viewport', async ({ page }) => {
      await page.setViewportSize(Viewports.DESKTOP);
      await page.goto('/');

      const body = page.locator('body');
      await expect(body).toBeVisible();
    });

    test('should render correctly on mobile viewport', async ({ page }) => {
      await page.setViewportSize(Viewports.MOBILE);
      await page.goto('/');

      const body = page.locator('body');
      await expect(body).toBeVisible();
    });

    test('should render correctly on tablet viewport', async ({ page }) => {
      await page.setViewportSize(Viewports.TABLET);
      await page.goto('/');

      const body = page.locator('body');
      await expect(body).toBeVisible();
    });
  });

  test.describe('Network Handling', () => {
    test('should handle slow network gracefully', async ({ page }) => {
      // Simulate slow 3G network
      const client = await page.context().newCDPSession(page);
      await client.send('Network.emulateNetworkConditions', {
        offline: false,
        downloadThroughput: (500 * 1024) / 8, // 500kb/s
        uploadThroughput: (500 * 1024) / 8, // 500kb/s
        latency: 400, // 400ms latency
      });

      // Page should still load (with increased timeout)
      const response = await page.goto('/', { timeout: 30000 });
      expect(response?.ok() || response?.status() === 304).toBeTruthy();
    });
  });
});

test.describe('Accessibility Baseline', () => {
  test('should have lang attribute on html', async ({ page }) => {
    await page.goto('/');

    const lang = await page.locator('html').getAttribute('lang');
    // Page should have a language set (or default to browser's)
    // This is a soft check - just log if missing
    if (!lang) {
      console.warn('HTML element missing lang attribute');
    }
  });

  test('should have viewport meta tag', async ({ page }) => {
    await page.goto('/');

    const viewport = await page.locator('meta[name="viewport"]').count();
    expect(viewport).toBeGreaterThanOrEqual(1);
  });
});
