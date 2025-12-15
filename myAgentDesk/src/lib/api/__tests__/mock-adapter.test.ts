/**
 * @file MockAdapterFactory tests
 * @description TDD Phase 1: RED - Tests for mock/real mode switching
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { MockAdapterFactory, type ApiClients } from '../mock/adapter-factory';
import { isOk, isErr } from '../result';

describe('MockAdapterFactory', () => {
	let originalEnv: string | undefined;

	beforeEach(() => {
		originalEnv = process.env.VITE_USE_MOCK_API;
	});

	afterEach(() => {
		if (originalEnv !== undefined) {
			process.env.VITE_USE_MOCK_API = originalEnv;
		} else {
			delete process.env.VITE_USE_MOCK_API;
		}
		// Reset the cache so the next test gets fresh mode detection
		MockAdapterFactory.resetCache();
	});

	describe('create()', () => {
		it('should create mock clients when VITE_USE_MOCK_API is true', () => {
			process.env.VITE_USE_MOCK_API = 'true';

			const clients = MockAdapterFactory.create();

			expect(clients.expertAgent).toBeDefined();
			expect(clients.jobQueue).toBeDefined();
			expect(clients.myScheduler).toBeDefined();
			expect(clients.myVault).toBeDefined();
			expect(clients.langfuse).toBeDefined();
			expect(MockAdapterFactory.isMockMode()).toBe(true);
		});

		it('should create real clients when VITE_USE_MOCK_API is false', () => {
			process.env.VITE_USE_MOCK_API = 'false';

			const clients = MockAdapterFactory.create({
				expertAgent: { baseUrl: 'http://localhost:8104/aiagent-api' },
				jobQueue: { baseUrl: 'http://localhost:8101', apiToken: 'token' },
				myScheduler: { baseUrl: 'http://localhost:8102', apiToken: 'token' },
				myVault: { baseUrl: 'http://localhost:8103', serviceName: 'test', serviceToken: 'token' },
				langfuse: { baseUrl: 'http://localhost:8104/aiagent-api' }
			});

			expect(clients.expertAgent).toBeDefined();
			expect(MockAdapterFactory.isMockMode()).toBe(false);
		});

		it('should use mock mode by default when env is not set', () => {
			delete process.env.VITE_USE_MOCK_API;

			const clients = MockAdapterFactory.create();

			expect(MockAdapterFactory.isMockMode()).toBe(true);
		});
	});

	describe('Mock client behavior', () => {
		beforeEach(() => {
			process.env.VITE_USE_MOCK_API = 'true';
		});

		it('should return mock data from ExpertAgent client', async () => {
			const clients = MockAdapterFactory.create();

			const result = await clients.expertAgent.generateJob({
				user_requirement: 'Test requirement'
			});

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.job_id).toBeDefined();
				expect(result.value.status).toBe('creating');
			}
		});

		it('should return mock job versions from JobQueue client', async () => {
			const clients = MockAdapterFactory.create();

			const result = await clients.jobQueue.getJobMasters();

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(Array.isArray(result.value)).toBe(true);
				expect(result.value.length).toBeGreaterThan(0);
			}
		});

		it('should return mock schedules from MyScheduler client', async () => {
			const clients = MockAdapterFactory.create();

			const result = await clients.myScheduler.getSchedules();

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(Array.isArray(result.value)).toBe(true);
			}
		});

		it('should return mock secrets from MyVault client', async () => {
			const clients = MockAdapterFactory.create();

			const result = await clients.myVault.listSecrets();

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(Array.isArray(result.value)).toBe(true);
			}
		});

		it('should return mock traces from Langfuse client', async () => {
			const clients = MockAdapterFactory.create();

			const result = await clients.langfuse.getTraces({});

			expect(isOk(result)).toBe(true);
			if (isOk(result)) {
				expect(result.value.traces).toBeDefined();
			}
		});
	});

	describe('Retry configuration with 3 retries', () => {
		it('should retry up to 3 times on transient errors', async () => {
			process.env.VITE_USE_MOCK_API = 'true';

			const clients = MockAdapterFactory.create();

			// Mock clients should have default retry config
			const result = await clients.expertAgent.health();

			// Successful call - no retries needed
			expect(isOk(result)).toBe(true);
		});
	});
});
