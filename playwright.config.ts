import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright設定ファイル
 * 受入テストの自動実行用に最適化
 */
export default defineConfig({
  // テストディレクトリ
  testDir: './tests/e2e',

  // テストマッチパターン
  testMatch: [
    '**/*.spec.ts',
    '**/*.e2e.ts',
    '**/acceptance-*.ts'
  ],

  // 並列実行設定
  fullyParallel: true,
  workers: process.env.CI ? 2 : undefined,

  // リトライ設定
  retries: process.env.CI ? 2 : 1,

  // レポート設定
  reporter: [
    // ターミナル出力
    ['list'],
    // HTML レポート
    ['html', {
      outputFolder: 'test-results/playwright-report',
      open: 'never'
    }],
    // JSON レポート（CI/CD用）
    ['json', {
      outputFile: 'test-results/results.json'
    }],
    // JUnit XML（CI/CD統合用）
    ['junit', {
      outputFile: 'test-results/junit.xml'
    }]
  ],

  // グローバル設定
  use: {
    // ベースURL
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // トレース設定（失敗時のみ）
    trace: 'on-first-retry',

    // スクリーンショット設定
    screenshot: {
      mode: 'only-on-failure',
      fullPage: true
    },

    // ビデオ録画設定
    video: {
      mode: 'retain-on-failure',
      size: { width: 1280, height: 720 }
    },

    // アクションのタイムアウト
    actionTimeout: 10 * 1000,

    // ナビゲーションのタイムアウト
    navigationTimeout: 30 * 1000,
  },

  // タイムアウト設定
  timeout: 30 * 1000,
  expect: {
    timeout: 5 * 1000,
  },

  // プロジェクト設定（ブラウザ別）
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 }
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        viewport: { width: 1920, height: 1080 }
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        viewport: { width: 1920, height: 1080 }
      },
    },
    // モバイルテスト
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
      },
    },
    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 12'],
      },
    },
    // APIテスト専用
    {
      name: 'api',
      use: {
        baseURL: process.env.API_URL || 'http://localhost:8000',
        extraHTTPHeaders: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      },
    },
  ],

  // 開発サーバー設定
  webServer: process.env.CI ? undefined : {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: true,
    timeout: 120 * 1000,
  },

  // アウトプットフォルダ
  outputDir: 'test-results/artifacts',
});