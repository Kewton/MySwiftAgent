/**
 * Vitest Setup File
 *
 * This file is executed before each test file.
 * It sets up the testing environment and global configurations.
 */

import { beforeAll, afterAll } from 'vitest';

// Set test environment
process.env.NODE_ENV = 'test';

// Global setup
beforeAll(() => {
  console.log('Starting TypeScript integration tests...');
});

// Global teardown
afterAll(() => {
  console.log('TypeScript integration tests completed.');
});
