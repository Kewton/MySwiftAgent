/**
 * Test Utilities for TypeScript Integration Tests
 *
 * Common helper functions and utilities for integration testing.
 */

import { beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

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

/**
 * Common test YAML templates for GraphAI workflows
 */
export const YAML_TEMPLATES = {
  /**
   * Simple workflow template with a single value node
   * @param value - The value to set in the node
   */
  simple: (value: string = 'Test') => `version: 0.5
nodes:
  test_node:
    value: "${value}"
`,

  /**
   * Complex workflow template with multiple nodes
   */
  complex: `version: 0.5
nodes:
  source:
    value: {}
  llm_node:
    agent: openAIAgent
    params:
      model: gpt-4
    inputs:
      - :source
  output_node:
    agent: copyAgent
    inputs:
      - :llm_node
`,
} as const;

/**
 * File cleanup utility for test workflow files
 */
export interface FileCleanupConfig {
  /** Base directory where files are created */
  baseDir: string;
  /** File extension to match (default: '.yml') */
  extension?: string;
}

/**
 * Create a file cleanup manager for test files
 * @param config - Configuration for file cleanup
 * @returns Object with cleanup methods
 */
export function createFileCleanup(config: FileCleanupConfig) {
  const { baseDir, extension = '.yml' } = config;
  const trackedFiles: string[] = [];

  return {
    /**
     * Track a file for cleanup
     */
    track(filename: string): void {
      if (!trackedFiles.includes(filename)) {
        trackedFiles.push(filename);
      }
    },

    /**
     * Get the full path for a tracked file
     */
    getPath(filename: string): string {
      return path.join(baseDir, `${filename}${extension}`);
    },

    /**
     * Clean up all tracked files
     */
    cleanup(): void {
      trackedFiles.forEach((filename) => {
        const filePath = path.join(baseDir, `${filename}${extension}`);
        if (fs.existsSync(filePath)) {
          fs.unlinkSync(filePath);
        }
      });
    },

    /**
     * Clean up the base directory if empty
     */
    cleanupDirectory(): void {
      if (fs.existsSync(baseDir)) {
        try {
          const files = fs.readdirSync(baseDir);
          if (files.length === 0) {
            fs.rmdirSync(baseDir);
            const parentDir = path.dirname(baseDir);
            if (fs.existsSync(parentDir) && fs.readdirSync(parentDir).length === 0) {
              fs.rmdirSync(parentDir);
            }
          }
        } catch {
          // Ignore cleanup errors
        }
      }
    },

    /**
     * Reset tracked files list
     */
    reset(): void {
      trackedFiles.length = 0;
    },
  };
}
