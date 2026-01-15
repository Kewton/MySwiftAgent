/**
 * Vitest setup file
 *
 * This file runs before all tests and sets up the test environment.
 */

import { beforeAll, afterAll, beforeEach } from 'vitest';

// Set base test environment variables
beforeAll(() => {
  process.env['NODE_ENV'] = 'test';
  process.env['PORT'] = '8006';
});

// Don't set security env vars globally - let tests manage them
// This prevents interference between tests

afterAll(() => {
  // Cleanup if needed
});
