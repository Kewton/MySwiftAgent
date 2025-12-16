/**
 * @file RetryHandler implementation
 * @description Exponential backoff retry logic for API calls
 */

import { type Result, isErr } from '../result';
import { type ApiError, isRetryableError } from '../errors';

/**
 * Retry configuration
 */
export interface RetryConfig {
	/** Maximum number of retry attempts */
	maxRetries: number;
	/** Base delay in milliseconds */
	baseDelayMs: number;
	/** Maximum delay in milliseconds */
	maxDelayMs: number;
}

/**
 * Default retry configuration
 */
const DEFAULT_CONFIG: RetryConfig = {
	maxRetries: 3,
	baseDelayMs: 1000,
	maxDelayMs: 30000
};

/**
 * Async operation type
 */
export type AsyncOperation<T> = () => Promise<Result<T, ApiError>>;

/**
 * Retry handler with exponential backoff
 */
export class RetryHandler {
	readonly config: RetryConfig;

	constructor(config?: Partial<RetryConfig>) {
		this.config = { ...DEFAULT_CONFIG, ...config };
	}

	/**
	 * Calculate delay for a retry attempt using exponential backoff
	 * @param attempt - Zero-based attempt number
	 * @returns Delay in milliseconds
	 */
	calculateDelay(attempt: number): number {
		const delay = this.config.baseDelayMs * Math.pow(2, attempt);
		return Math.min(delay, this.config.maxDelayMs);
	}

	/**
	 * Determine if an error should trigger a retry
	 * @param error - The API error
	 * @param attempt - Current attempt number (zero-based)
	 * @returns Whether to retry
	 */
	shouldRetry(error: ApiError, attempt: number): boolean {
		// Don't retry if we've exceeded max retries
		if (attempt >= this.config.maxRetries) {
			return false;
		}

		// Only retry on retryable errors
		return isRetryableError(error);
	}

	/**
	 * Execute an operation with retry logic
	 * @param operation - The async operation to execute
	 * @returns The result of the operation
	 */
	async execute<T>(operation: AsyncOperation<T>): Promise<Result<T, ApiError>> {
		let attempt = 0;
		let result = await operation();

		while (isErr(result) && this.shouldRetry(result.error, attempt)) {
			const delay = this.calculateDelay(attempt);
			await this.sleep(delay);
			attempt++;
			result = await operation();
		}

		return result;
	}

	/**
	 * Sleep for a given duration
	 */
	private sleep(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
