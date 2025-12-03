/**
 * Test Configuration Module
 *
 * Centralized configuration for acceptance tests.
 * All environment variables and default values are defined here
 * to ensure consistency across test files.
 *
 * @module config/test-config
 */

/**
 * Service URLs configuration.
 * Each service URL can be overridden via environment variables.
 */
export const ServiceUrls = {
  /** myAgentDesk frontend URL */
  MYAGENTDESK: process.env.MYAGENTDESK_URL || 'http://localhost:5173',

  /** ExpertAgent API URL */
  EXPERTAGENT: process.env.EXPERTAGENT_URL || 'http://localhost:8004',

  /** JobQueue API URL */
  JOBQUEUE: process.env.JOBQUEUE_URL || 'http://localhost:8001',

  /** MyVault API URL */
  MYVAULT: process.env.MYVAULT_URL || 'http://localhost:8003',
} as const;

/**
 * Timeout configuration values in milliseconds.
 */
export const Timeouts = {
  /** Default test timeout */
  TEST: 60 * 1000, // 60 seconds

  /** Expect assertion timeout */
  EXPECT: 10 * 1000, // 10 seconds

  /** Action timeout (clicks, types, etc.) */
  ACTION: 15 * 1000, // 15 seconds

  /** Navigation timeout */
  NAVIGATION: 30 * 1000, // 30 seconds

  /** Short timeout for quick operations */
  SHORT: 5 * 1000, // 5 seconds

  /** Health check request timeout */
  HEALTH_CHECK: 5 * 1000, // 5 seconds

  /** Page load performance baseline */
  PAGE_LOAD_BASELINE: 5 * 1000, // 5 seconds

  /** Maximum acceptable page load time */
  PAGE_LOAD_MAX: 10 * 1000, // 10 seconds
} as const;

/**
 * Viewport configurations for responsive testing.
 */
export const Viewports = {
  DESKTOP: { width: 1280, height: 720 },
  TABLET: { width: 768, height: 1024 },
  MOBILE: { width: 375, height: 667 },
} as const;

/**
 * Performance thresholds for testing.
 */
export const PerformanceThresholds = {
  /** Maximum DOM element count */
  MAX_DOM_ELEMENTS: 5000,
} as const;

/**
 * Feature flags for conditional test execution.
 */
export const FeatureFlags = {
  /** Enable backend health checks (set CHECK_BACKEND_HEALTH=1) */
  CHECK_BACKEND_HEALTH: !!process.env.CHECK_BACKEND_HEALTH,

  /** Running in CI environment */
  IS_CI: !!process.env.CI,
} as const;

/**
 * Get health endpoint URL for a service.
 *
 * @param baseUrl - The base URL of the service
 * @returns Full health endpoint URL
 */
export function getHealthEndpoint(baseUrl: string): string {
  return `${baseUrl}/health`;
}
