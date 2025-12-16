/**
 * @file API module exports
 * @description Centralized exports for the API client layer
 */

// Core types
export * from './result';
export * from './errors';
export * from './types';

// Configuration
export * from './config';

// Base infrastructure
export {
	ApiClient,
	type ApiClientConfig,
	type AuthType,
	type RequestOptions
} from './base/api-client';
export { RetryHandler, type RetryConfig, type AsyncOperation } from './base/retry-handler';
export { CircuitBreaker, CircuitState, type CircuitBreakerConfig } from './base/circuit-breaker';

// API clients
export {
	ExpertAgentClient,
	type ExpertAgentClientConfig,
	type GenerateJobRequest,
	type GenerateJobResponse,
	type JobStatusResponse,
	type HealthResponse
} from './clients/expert-agent';

export {
	JobQueueClient,
	type JobQueueClientConfig,
	type CreateJobRequest,
	type JobResponse,
	type JobListFilter,
	type JobMasterResponse,
	type TaskMasterResponse
} from './clients/job-queue';

export {
	MySchedulerClient,
	type MySchedulerClientConfig,
	type CreateScheduleRequest,
	type ScheduleResponse
} from './clients/my-scheduler';

export {
	MyVaultClient,
	type MyVaultClientConfig,
	type SecretResponse,
	type CreateSecretRequest,
	type UpdateSecretRequest
} from './clients/my-vault';

export {
	LangfuseClient,
	type LangfuseClientConfig,
	type TraceFilter,
	type TraceResponse,
	type TraceObservation,
	type TracesListResponse,
	type SubmitScoreRequest,
	type SubmitScoreResponse
} from './clients/langfuse';

// Mock implementations
export { MockAdapterFactory, type ApiClients, type ApiClientConfigs } from './mock/adapter-factory';
export { ExpertAgentClientMock } from './mock/expert-agent.mock';
export { JobQueueClientMock } from './mock/job-queue.mock';
export { MySchedulerClientMock } from './mock/my-scheduler.mock';
export { MyVaultClientMock } from './mock/my-vault.mock';
export { LangfuseClientMock } from './mock/langfuse.mock';

/**
 * Create API clients (convenience function)
 * Uses mock mode when VITE_USE_MOCK_API=true
 */
export function createApiClients(configs?: import('./mock/adapter-factory').ApiClientConfigs) {
	return import('./mock/adapter-factory').then(({ MockAdapterFactory }) =>
		MockAdapterFactory.create(configs)
	);
}

/**
 * Synchronous API client factory using MockAdapterFactory
 */
export { MockAdapterFactory as api } from './mock/adapter-factory';
