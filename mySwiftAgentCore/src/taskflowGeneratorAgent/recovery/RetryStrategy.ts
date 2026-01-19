/**
 * RetryStrategy - Retry logic with exponential backoff
 *
 * Issue #364: Retry mechanism for transient failures
 */

/**
 * Retry Configuration
 */
export interface RetryConfig {
  maxAttempts: number;
  initialDelayMs: number;
  maxDelayMs: number;
  backoffFactor: number;
}

/**
 * Retry callback types
 */
export type ShouldRetryFn = (error: Error, attempt: number) => boolean;
export type OnRetryFn = (error: Error, attempt: number, delayMs: number) => void;

/**
 * Default retry configuration
 */
const DEFAULT_CONFIG: RetryConfig = {
  maxAttempts: 3,
  initialDelayMs: 1000,
  maxDelayMs: 10000,
  backoffFactor: 2,
};

/**
 * RetryStrategy - Implements retry with exponential backoff
 *
 * Features:
 * - Configurable max attempts
 * - Exponential backoff with configurable factor
 * - Maximum delay cap
 * - Custom retry predicates
 * - Retry callbacks
 */
export class RetryStrategy {
  private readonly config: RetryConfig;

  constructor(config: Partial<RetryConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Execute function with retry logic
   *
   * @param fn - Function to execute (receives attempt number)
   * @param shouldRetry - Optional predicate to determine if retry should happen
   * @param onRetry - Optional callback when retry occurs
   * @returns Result of function execution
   */
  async execute<T>(
    fn: (attempt: number) => Promise<T>,
    shouldRetry?: ShouldRetryFn,
    onRetry?: OnRetryFn
  ): Promise<T> {
    let lastError: Error | undefined;

    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt++) {
      try {
        return await fn(attempt);
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Check if we should retry
        const retryPredicate = shouldRetry ?? this.shouldRetryDefault.bind(this);
        if (!retryPredicate(lastError, attempt)) {
          throw lastError;
        }

        // Check if we have more attempts
        if (attempt >= this.config.maxAttempts) {
          throw lastError;
        }

        // Calculate delay and wait
        const delayMs = this.calculateDelay(attempt);

        // Call onRetry callback
        if (onRetry) {
          onRetry(lastError, attempt, delayMs);
        }

        await this.delay(delayMs);
      }
    }

    // Should not reach here, but TypeScript needs this
    throw lastError ?? new Error('Retry failed');
  }

  /**
   * Calculate delay for given attempt using exponential backoff
   *
   * @param attempt - Current attempt number (1-based)
   * @returns Delay in milliseconds
   */
  calculateDelay(attempt: number): number {
    // Exponential backoff: initialDelay * (backoffFactor ^ (attempt - 1))
    const exponentialDelay =
      this.config.initialDelayMs * Math.pow(this.config.backoffFactor, attempt - 1);

    // Cap at maxDelay
    return Math.min(exponentialDelay, this.config.maxDelayMs);
  }

  /**
   * Default should retry predicate
   * Override this or pass custom predicate to execute()
   */
  shouldRetryDefault(_error: Error, _attempt: number): boolean {
    // By default, retry all errors
    // Subclasses or callers can provide more specific logic
    return true;
  }

  /**
   * Get current configuration
   */
  getConfig(): RetryConfig {
    return { ...this.config };
  }

  /**
   * Get maximum attempts
   *
   * Issue #374: Helper method for feedback loop integration
   */
  getMaxAttempts(): number {
    return this.config.maxAttempts;
  }

  /**
   * Delay for specified milliseconds
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

/**
 * Factory function
 */
export function createRetryStrategy(config?: Partial<RetryConfig>): RetryStrategy {
  return new RetryStrategy(config);
}
