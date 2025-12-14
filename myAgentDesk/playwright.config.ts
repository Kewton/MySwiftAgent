import type { PlaywrightTestConfig } from '@playwright/test';

const config: PlaywrightTestConfig = {
	webServer: {
		command: 'npm run build && npm run preview',
		port: 4173
	},
	testDir: 'tests/e2e',
	testMatch: /(.+\.)?(test|spec)\.[jt]s/,
	timeout: 30000,
	retries: 0,
	use: {
		baseURL: 'http://localhost:4173',
		trace: 'on-first-retry'
	}
};

export default config;
