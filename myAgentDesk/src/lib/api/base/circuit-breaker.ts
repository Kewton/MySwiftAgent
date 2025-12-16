/**
 * @file CircuitBreaker implementation
 * @description Circuit breaker pattern for fault tolerance
 */

import { type Result, err, isOk } from '../result';
import { type ApiError, ApiErrorCode, createApiError, isRetryableError } from '../errors';

/**
 * Circuit breaker states
 */
export enum CircuitState {
	CLOSED = 'CLOSED',
	OPEN = 'OPEN',
	HALF_OPEN = 'HALF_OPEN'
}

/**
 * Circuit breaker configuration
 */
export interface CircuitBreakerConfig {
	/** Number of failures before opening the circuit */
	failureThreshold: number;
	/** Time in ms before transitioning from OPEN to HALF_OPEN */
	resetTimeoutMs: number;
	/** Number of successful requests in HALF_OPEN before closing */
	halfOpenMaxAttempts: number;
}

/**
 * Default circuit breaker configuration
 */
const DEFAULT_CONFIG: CircuitBreakerConfig = {
	failureThreshold: 5,
	resetTimeoutMs: 30000,
	halfOpenMaxAttempts: 3
};

/**
 * Async operation type
 */
export type AsyncOperation<T> = () => Promise<Result<T, ApiError>>;

/**
 * Circuit breaker for fault tolerance
 */
export class CircuitBreaker {
	readonly config: CircuitBreakerConfig;

	private _state: CircuitState = CircuitState.CLOSED;
	private _failureCount: number = 0;
	private _lastFailureTime: number = 0;
	private _halfOpenAttempts: number = 0;

	constructor(config?: Partial<CircuitBreakerConfig>) {
		this.config = { ...DEFAULT_CONFIG, ...config };
	}

	/**
	 * Current circuit state
	 */
	get state(): CircuitState {
		// Check if we should transition from OPEN to HALF_OPEN
		if (this._state === CircuitState.OPEN) {
			const timeSinceFailure = Date.now() - this._lastFailureTime;
			if (timeSinceFailure >= this.config.resetTimeoutMs) {
				this._state = CircuitState.HALF_OPEN;
				this._halfOpenAttempts = 0;
			}
		}
		return this._state;
	}

	/**
	 * Current failure count
	 */
	get failureCount(): number {
		return this._failureCount;
	}

	/**
	 * Execute an operation through the circuit breaker
	 */
	async execute<T>(operation: AsyncOperation<T>): Promise<Result<T, ApiError>> {
		const currentState = this.state;

		// If circuit is OPEN, reject immediately
		if (currentState === CircuitState.OPEN) {
			return err(
				createApiError({
					code: ApiErrorCode.CIRCUIT_OPEN,
					message: 'Circuit breaker is open'
				})
			);
		}

		// Execute the operation
		const result = await operation();

		// Handle result based on state
		if (isOk(result)) {
			this.onSuccess();
		} else {
			this.onFailure(result.error);
		}

		return result;
	}

	/**
	 * Handle successful operation
	 */
	private onSuccess(): void {
		if (this._state === CircuitState.HALF_OPEN) {
			// Success in HALF_OPEN - close the circuit
			this._state = CircuitState.CLOSED;
		}
		// Reset failure count on success
		this._failureCount = 0;
	}

	/**
	 * Handle failed operation
	 */
	private onFailure(error: ApiError): void {
		// Only count retryable errors towards the circuit breaker
		if (!isRetryableError(error)) {
			return;
		}

		if (this._state === CircuitState.HALF_OPEN) {
			// Failure in HALF_OPEN - back to OPEN
			this._state = CircuitState.OPEN;
			this._lastFailureTime = Date.now();
			return;
		}

		// Increment failure count
		this._failureCount++;
		this._lastFailureTime = Date.now();

		// Check if we should open the circuit
		if (this._failureCount >= this.config.failureThreshold) {
			this._state = CircuitState.OPEN;
		}
	}

	/**
	 * Reset the circuit breaker to initial state
	 */
	reset(): void {
		this._state = CircuitState.CLOSED;
		this._failureCount = 0;
		this._lastFailureTime = 0;
		this._halfOpenAttempts = 0;
	}
}
