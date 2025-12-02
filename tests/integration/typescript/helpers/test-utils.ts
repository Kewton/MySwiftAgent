/**
 * Test Utilities for TypeScript Integration Tests
 *
 * Common helper functions and utilities for integration testing.
 */

import { beforeEach, afterEach } from 'vitest';

/**
 * Check if a service is available at the given URL
 * @param url - The URL to check
 * @param timeout - Timeout in milliseconds (default: 5000)
 * @returns Promise<boolean> - True if service is available
 */
export async function isServiceAvailable(
  url: string,
  timeout: number = 5000
): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method: 'GET',
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    clearTimeout(timeoutId);
    return false;
  }
}

/**
 * Skip test if service is not available
 * @param serviceName - Name of the service for logging
 * @param healthUrl - Health check URL
 */
export async function skipIfServiceUnavailable(
  serviceName: string,
  healthUrl: string
): Promise<void> {
  const available = await isServiceAvailable(healthUrl);
  if (!available) {
    console.log(`Skipping tests: ${serviceName} is not available at ${healthUrl}`);
  }
}

/**
 * Create a test context with setup and cleanup
 */
export function createTestContext<T>(
  setup: () => T | Promise<T>,
  cleanup?: (context: T) => void | Promise<void>
): { getContext: () => T } {
  let context: T;

  beforeEach(async () => {
    context = await setup();
  });

  afterEach(async () => {
    if (cleanup) {
      await cleanup(context);
    }
  });

  return {
    getContext: () => context,
  };
}

/**
 * Wait for a condition to be true
 * @param condition - Function that returns true when condition is met
 * @param timeout - Maximum time to wait in milliseconds
 * @param interval - Polling interval in milliseconds
 */
export async function waitFor(
  condition: () => boolean | Promise<boolean>,
  timeout: number = 5000,
  interval: number = 100
): Promise<void> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  throw new Error(`Condition not met within ${timeout}ms`);
}
