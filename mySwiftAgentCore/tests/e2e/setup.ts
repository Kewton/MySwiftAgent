/**
 * E2E Test Setup
 *
 * Issue #379: Setup file for E2E tests
 */

import { beforeAll, afterAll } from 'vitest';

// Set test environment variables
beforeAll(() => {
  process.env['NODE_ENV'] = 'test';
  process.env['PORT'] = '8006';
  // Enable MSW in test environment
  process.env['MSW_ENABLED'] = 'true';
});

afterAll(() => {
  // Cleanup if needed
});
