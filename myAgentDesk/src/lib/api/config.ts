/**
 * @file API configuration
 * @description Configuration for API clients and environment settings
 */

/**
 * API endpoint configuration
 */
export interface ApiEndpointConfig {
	baseUrl: string;
	timeout?: number;
}

/**
 * Complete API configuration
 */
export interface ApiConfig {
	expertAgent: ApiEndpointConfig & {
		adminToken?: string;
	};
	jobQueue: ApiEndpointConfig & {
		apiToken: string;
	};
	myScheduler: ApiEndpointConfig & {
		apiToken: string;
	};
	myVault: ApiEndpointConfig & {
		serviceName: string;
		serviceToken: string;
	};
	langfuse: ApiEndpointConfig & {
		adminToken?: string;
	};
}

/**
 * Default configuration values
 */
export const DEFAULT_CONFIG: ApiConfig = {
	expertAgent: {
		baseUrl: 'http://localhost:8004/aiagent-api',
		timeout: 30000
	},
	jobQueue: {
		baseUrl: 'http://localhost:8001',
		apiToken: '',
		timeout: 30000
	},
	myScheduler: {
		baseUrl: 'http://localhost:8002',
		apiToken: '',
		timeout: 30000
	},
	myVault: {
		baseUrl: 'http://localhost:8003',
		serviceName: 'myAgentDesk',
		serviceToken: '',
		timeout: 30000
	},
	langfuse: {
		baseUrl: 'http://localhost:3001',
		timeout: 30000
	}
};

/**
 * Load configuration from environment variables
 */
export function loadConfigFromEnv(): ApiConfig {
	const getEnv = (key: string, defaultValue = ''): string => {
		if (typeof import.meta !== 'undefined' && import.meta.env) {
			return (import.meta.env[key] as string) ?? defaultValue;
		}
		if (typeof process !== 'undefined' && process.env) {
			return process.env[key] ?? defaultValue;
		}
		return defaultValue;
	};

	return {
		expertAgent: {
			baseUrl: getEnv('VITE_EXPERT_AGENT_URL', DEFAULT_CONFIG.expertAgent.baseUrl),
			adminToken: getEnv('VITE_EXPERT_AGENT_ADMIN_TOKEN'),
			timeout: parseInt(getEnv('VITE_EXPERT_AGENT_TIMEOUT', '30000'), 10)
		},
		jobQueue: {
			baseUrl: getEnv('VITE_JOBQUEUE_URL', DEFAULT_CONFIG.jobQueue.baseUrl),
			apiToken: getEnv('VITE_JOBQUEUE_API_TOKEN', ''),
			timeout: parseInt(getEnv('VITE_JOBQUEUE_TIMEOUT', '30000'), 10)
		},
		myScheduler: {
			baseUrl: getEnv('VITE_MYSCHEDULER_URL', DEFAULT_CONFIG.myScheduler.baseUrl),
			apiToken: getEnv('VITE_MYSCHEDULER_API_TOKEN', ''),
			timeout: parseInt(getEnv('VITE_MYSCHEDULER_TIMEOUT', '30000'), 10)
		},
		myVault: {
			baseUrl: getEnv('VITE_MYVAULT_URL', DEFAULT_CONFIG.myVault.baseUrl),
			serviceName: getEnv('VITE_MYVAULT_SERVICE_NAME', 'myAgentDesk'),
			serviceToken: getEnv('VITE_MYVAULT_SERVICE_TOKEN', ''),
			timeout: parseInt(getEnv('VITE_MYVAULT_TIMEOUT', '30000'), 10)
		},
		langfuse: {
			baseUrl: getEnv('VITE_LANGFUSE_URL', DEFAULT_CONFIG.langfuse.baseUrl),
			adminToken: getEnv('VITE_LANGFUSE_ADMIN_TOKEN'),
			timeout: parseInt(getEnv('VITE_LANGFUSE_TIMEOUT', '30000'), 10)
		}
	};
}

/**
 * Retry configuration
 */
export interface RetryConfiguration {
	maxRetries: number;
	baseDelayMs: number;
	maxDelayMs: number;
}

/**
 * Default retry configuration
 */
export const DEFAULT_RETRY_CONFIG: RetryConfiguration = {
	maxRetries: 3,
	baseDelayMs: 1000,
	maxDelayMs: 30000
};

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfiguration {
	failureThreshold: number;
	resetTimeoutMs: number;
	halfOpenMaxAttempts: number;
}

/**
 * Default circuit breaker configuration
 */
export const DEFAULT_CIRCUIT_BREAKER_CONFIG: CircuitBreakerConfiguration = {
	failureThreshold: 5,
	resetTimeoutMs: 30000,
	halfOpenMaxAttempts: 3
};
