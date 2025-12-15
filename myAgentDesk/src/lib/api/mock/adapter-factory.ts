/**
 * @file MockAdapterFactory implementation
 * @description Factory for creating mock or real API clients based on environment
 */

import { ExpertAgentClient, type ExpertAgentClientConfig } from '../clients/expert-agent';
import { JobQueueClient, type JobQueueClientConfig } from '../clients/job-queue';
import { MySchedulerClient, type MySchedulerClientConfig } from '../clients/my-scheduler';
import { MyVaultClient, type MyVaultClientConfig } from '../clients/my-vault';
import { LangfuseClient, type LangfuseClientConfig } from '../clients/langfuse';

import { ExpertAgentClientMock } from './expert-agent.mock';
import { JobQueueClientMock } from './job-queue.mock';
import { MySchedulerClientMock } from './my-scheduler.mock';
import { MyVaultClientMock } from './my-vault.mock';
import { LangfuseClientMock } from './langfuse.mock';

/**
 * API client configurations
 */
export interface ApiClientConfigs {
	expertAgent?: ExpertAgentClientConfig;
	jobQueue?: JobQueueClientConfig;
	myScheduler?: MySchedulerClientConfig;
	myVault?: MyVaultClientConfig;
	langfuse?: LangfuseClientConfig;
}

/**
 * API clients interface
 */
export interface ApiClients {
	expertAgent: ExpertAgentClient | ExpertAgentClientMock;
	jobQueue: JobQueueClient | JobQueueClientMock;
	myScheduler: MySchedulerClient | MySchedulerClientMock;
	myVault: MyVaultClient | MyVaultClientMock;
	langfuse: LangfuseClient | LangfuseClientMock;
}

/**
 * Check if mock mode is enabled
 */
function isMockModeEnabled(): boolean {
	// Check for Vite environment variable
	if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_USE_MOCK_API) {
		return import.meta.env.VITE_USE_MOCK_API === 'true';
	}
	// Check for Node.js environment variable
	if (typeof process !== 'undefined' && process.env?.VITE_USE_MOCK_API) {
		return process.env.VITE_USE_MOCK_API === 'true';
	}
	// Default to mock mode if not set
	return true;
}

/**
 * Factory for creating API clients
 * Uses mock clients when VITE_USE_MOCK_API=true or not set
 */
export class MockAdapterFactory {
	private static _isMockMode: boolean | null = null;

	/**
	 * Check if currently in mock mode
	 */
	static isMockMode(): boolean {
		if (this._isMockMode === null) {
			this._isMockMode = isMockModeEnabled();
		}
		return this._isMockMode;
	}

	/**
	 * Create API clients based on environment
	 */
	static create(configs?: ApiClientConfigs): ApiClients {
		if (this.isMockMode()) {
			return this.createMockClients();
		}
		return this.createRealClients(configs ?? {});
	}

	/**
	 * Create mock clients
	 */
	private static createMockClients(): ApiClients {
		return {
			expertAgent: new ExpertAgentClientMock() as unknown as ExpertAgentClient,
			jobQueue: new JobQueueClientMock() as unknown as JobQueueClient,
			myScheduler: new MySchedulerClientMock() as unknown as MySchedulerClient,
			myVault: new MyVaultClientMock() as unknown as MyVaultClient,
			langfuse: new LangfuseClientMock() as unknown as LangfuseClient
		};
	}

	/**
	 * Create real clients with provided configurations
	 */
	private static createRealClients(configs: ApiClientConfigs): ApiClients {
		return {
			expertAgent: new ExpertAgentClient(
				configs.expertAgent ?? { baseUrl: 'http://localhost:8104/aiagent-api' }
			),
			jobQueue: new JobQueueClient(
				configs.jobQueue ?? { baseUrl: 'http://localhost:8101', apiToken: '' }
			),
			myScheduler: new MySchedulerClient(
				configs.myScheduler ?? { baseUrl: 'http://localhost:8102', apiToken: '' }
			),
			myVault: new MyVaultClient(
				configs.myVault ?? {
					baseUrl: 'http://localhost:8103',
					serviceName: 'myAgentDesk',
					serviceToken: ''
				}
			),
			langfuse: new LangfuseClient(
				configs.langfuse ?? { baseUrl: 'http://localhost:8104/aiagent-api' }
			)
		};
	}

	/**
	 * Reset mock mode cache (useful for testing)
	 */
	static resetCache(): void {
		this._isMockMode = null;
	}
}
