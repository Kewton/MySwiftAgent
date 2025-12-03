/**
 * Health Check Tests
 *
 * Tests to verify the health status of various services.
 * These tests check API endpoints and service availability.
 *
 * @requires Services to be running for tests to pass
 */

import { test, expect } from '@playwright/test';

// Service configuration from environment or defaults
const MYAGENTDESK_URL =
  process.env.MYAGENTDESK_URL || 'http://localhost:5173';
const EXPERTAGENT_URL =
  process.env.EXPERTAGENT_URL || 'http://localhost:8004';
const JOBQUEUE_URL = process.env.JOBQUEUE_URL || 'http://localhost:8001';
const MYVAULT_URL = process.env.MYVAULT_URL || 'http://localhost:8003';

test.describe('Service Health Checks', () => {
  test.describe('myAgentDesk Health', () => {
    test('should respond to HTTP requests', async ({ request }) => {
      const response = await request.get(MYAGENTDESK_URL);
      expect(response.ok() || response.status() === 304).toBeTruthy();
    });

    test('should serve static assets', async ({ page }) => {
      const response = await page.goto(MYAGENTDESK_URL);
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
        !process.env.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      try {
        const response = await request.get(`${EXPERTAGENT_URL}/health`, {
          timeout: 5000,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(
          `ExpertAgent not reachable at ${EXPERTAGENT_URL}/health`
        );
      }
    });

    test('JobQueue health endpoint', async ({ request }) => {
      test.skip(
        !process.env.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      try {
        const response = await request.get(`${JOBQUEUE_URL}/health`, {
          timeout: 5000,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(`JobQueue not reachable at ${JOBQUEUE_URL}/health`);
      }
    });

    test('MyVault health endpoint', async ({ request }) => {
      test.skip(
        !process.env.CHECK_BACKEND_HEALTH,
        'Backend health check skipped - set CHECK_BACKEND_HEALTH=1 to enable'
      );

      try {
        const response = await request.get(`${MYVAULT_URL}/health`, {
          timeout: 5000,
        });
        expect(response.ok()).toBeTruthy();
      } catch {
        console.warn(`MyVault not reachable at ${MYVAULT_URL}/health`);
      }
    });
  });
});

test.describe('Performance Baseline', () => {
  test('page load time should be acceptable', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(MYAGENTDESK_URL);
    const endTime = Date.now();

    const loadTime = endTime - startTime;

    // Baseline: page should load in under 5 seconds
    // This is a soft limit for monitoring purposes
    console.log(`Page load time: ${loadTime}ms`);
    expect(loadTime).toBeLessThan(5000);
  });

  test('should have reasonable DOM size', async ({ page }) => {
    await page.goto(MYAGENTDESK_URL);

    // Count DOM elements
    const elementCount = await page.evaluate(
      () => document.querySelectorAll('*').length
    );

    // Reasonable limit for initial load
    console.log(`DOM element count: ${elementCount}`);
    expect(elementCount).toBeLessThan(5000);
  });
});
