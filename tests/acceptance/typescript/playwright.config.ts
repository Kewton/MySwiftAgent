import { defineConfig, devices } from '@playwright/test';
import {
  ServiceUrls,
  Timeouts,
  Viewports,
  FeatureFlags,
} from './config/test-config';

/**
 * Playwright configuration for TypeScript acceptance tests.
 *
 * This configuration file sets up Playwright for running acceptance tests
 * against myAgentDesk and related services.
 *
 * **Note**: These tests are NOT run in CI - they require running services
 * and potentially API keys for full E2E scenarios.
 *
 * @module playwright.config
 * @see https://playwright.dev/docs/test-configuration
 * @see ./config/test-config.ts for centralized configuration values
 */
export default defineConfig({
  // Test directory
  testDir: '.',

  // Test file patterns
  testMatch: ['**/*.spec.ts', '**/*.test.ts'],

  // Timeout for each test
  timeout: Timeouts.TEST,

  // Expect timeout
  expect: {
    timeout: Timeouts.EXPECT,
  },

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: FeatureFlags.IS_CI,

  // Retry on CI only
  retries: FeatureFlags.IS_CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: FeatureFlags.IS_CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['list'],
    ['html', { outputFolder: '../../../reports/playwright-report', open: 'never' }],
  ],

  // Shared settings for all projects
  use: {
    // Base URL for navigation (from centralized config)
    baseURL: ServiceUrls.MYAGENTDESK,

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video recording
    video: 'retain-on-failure',

    // Browser viewport (from centralized config)
    viewport: Viewports.DESKTOP,

    // Action timeout (from centralized config)
    actionTimeout: Timeouts.ACTION,

    // Navigation timeout (from centralized config)
    navigationTimeout: Timeouts.NAVIGATION,
  },

  // Configure projects for different browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // Uncomment for additional browser testing
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    // Mobile viewports
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
  ],

  // Web server configuration (optional - start services externally)
  // webServer: {
  //   command: 'make dev-frontend',
  //   url: 'http://localhost:5173',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000,
  // },

  // Output directory for test artifacts
  outputDir: '../../../reports/test-results',
});
