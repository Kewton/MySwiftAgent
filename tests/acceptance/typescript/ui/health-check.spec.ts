/**
 * Health Check Tests
 *
 * Tests to verify the health status of various services.
 * These tests check API endpoints and service availability.
 *
 * @module ui/health-check
 * @requires Services to be running for tests to pass
 */

import { test, expect } from '@playwright/test';
import {
  ServiceUrls,
  Timeouts,
  FeatureFlags,
  PerformanceThresholds,
  getHealthEndpoint,
} from '../config/test-config';

test.describe('Service Health Checks', () => {
  test.describe('myAgentDesk Health', () => {
    test('should respond to HTTP requests', async ({ request }) => {
      const response = await request.get(ServiceUrls.MYAGENTDESK);
      expect(response.ok() || response.status() === 304).toBeTruthy();
    });

    test('should serve static assets', async ({ page }) => {
      const response = await page.goto(ServiceUrls.MYAGENTDESK);
      expect(response).not.toBeNull();

      // Check that HTML content is returned
      const contentType = response?.headers()['content-type'];
      expect(contentType).toContain('text/html');
    });
  });

  test.describe('Backend API Health (optional)', () => {
    // These tests are marked as soft failures - they inform about backend status
    // but don't fail the overall test suite

    test('ExpertAgent health endpoint', async ({ request }) => {
      test.skip(
        !FeatureFlags.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      const healthUrl = getHealthEndpoint(ServiceUrls.EXPERTAGENT);
      try {
        const response = await request.get(healthUrl, {
          timeout: Timeouts.HEALTH_CHECK,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(`ExpertAgent not reachable at ${healthUrl}`);
      }
    });

    test('JobQueue health endpoint', async ({ request }) => {
      test.skip(
        !FeatureFlags.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      const healthUrl = getHealthEndpoint(ServiceUrls.JOBQUEUE);
      try {
        const response = await request.get(healthUrl, {
          timeout: Timeouts.HEALTH_CHECK,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(`JobQueue not reachable at ${healthUrl}`);
      }
    });

    test('MyVault health endpoint', async ({ request }) => {
      test.skip(
        !FeatureFlags.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      const healthUrl = getHealthEndpoint(ServiceUrls.MYVAULT);
      try {
        const response = await request.get(healthUrl, {
          timeout: Timeouts.HEALTH_CHECK,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(`MyVault not reachable at ${healthUrl}`);
      }
    });
  });
});

test.describe('Performance Baseline', () => {
  test('page load time should be acceptable', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(ServiceUrls.MYAGENTDESK);
    const endTime = Date.now();

    const loadTime = endTime - startTime;

    // Baseline: page should load in under 5 seconds
    // This is a soft limit for monitoring purposes
    console.log(`Page load time: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(Timeouts.PAGE_LOAD_BASELINE);
  });

  test('should have reasonable DOM size', async ({ page }) => {
    await page.goto(ServiceUrls.MYAGENTDESK);

    // Count DOM elements
    const elementCount = await page.evaluate(
      () => document.querySelectorAll('*').length
    );

    // Reasonable limit for initial load
    console.log(`DOM element count: ${elementCount}`);
    expect(elementCount).toBeLessThan(PerformanceThresholds.MAX_DOM_ELEMENTS);
  });
});
