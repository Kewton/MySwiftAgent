import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['**/*.test.ts'],
    exclude: ['node_modules', 'dist'],
    setupFiles: ['./setup.ts'],
    testTimeout: 30000,
    hookTimeout: 30000,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules', 'dist', '**/*.test.ts', 'vitest.config.ts', 'setup.ts'],
    },
  },
  resolve: {
    alias: {
      '@graphAiServer': '../../../graphAiServer/src',
    },
  },
});
