/**
 * DebugValidationObserver - Observer for debug mode validation
 *
 * Issue #381: Debug mode observer implementation
 *
 * Features:
 * - Logs validation progress to console
 * - Collects validation timing metrics
 * - Provides summary formatting
 */

import type { ValidationResult } from '../../types/generator.js';
import type { ValidationObserver, ValidationLog, ValidatorMetric } from '../../types/validation.js';

/**
 * DebugValidationObserver - Implements ValidationObserver for debug mode
 */
export class DebugValidationObserver implements ValidationObserver {
  private logs: ValidationLog[] = [];

  /**
   * Called when a validator starts
   */
  onValidatorStart(validatorName: string): void {
    console.debug(`[DEBUG] Starting: ${validatorName}`);
  }

  /**
   * Called when a validator completes
   */
  onValidatorComplete(
    validatorName: string,
    result: ValidationResult,
    durationMs: number
  ): void {
    const errorCount = result.errors?.length ?? 0;
    console.debug(
      `[DEBUG] Completed: ${validatorName} in ${durationMs}ms (errors: ${errorCount})`
    );

    this.logs.push({
      validatorName,
      result,
      durationMs,
      timestamp: new Date(),
    });
  }

  /**
   * Called when a validator throws an error
   */
  onError(validatorName: string, error: Error): void {
    console.error(`[DEBUG] Error in ${validatorName}: ${error.message}`);
  }

  /**
   * Get all validation logs
   * @returns Copy of logs array
   */
  getLogs(): ValidationLog[] {
    return [...this.logs];
  }

  /**
   * Clear all logs
   */
  clearLogs(): void {
    this.logs = [];
  }

  /**
   * Get total duration of all validations
   */
  getTotalDuration(): number {
    return this.logs.reduce((sum, log) => sum + log.durationMs, 0);
  }

  /**
   * Get total error count across all validators
   */
  getErrorCount(): number {
    return this.logs.reduce((sum, log) => sum + (log.result.errors?.length ?? 0), 0);
  }

  /**
   * Get metrics for a specific validator
   */
  getValidatorMetrics(validatorName: string): ValidatorMetric | undefined {
    const log = this.logs.find((l) => l.validatorName === validatorName);
    if (!log) {
      return undefined;
    }
    return {
      durationMs: log.durationMs,
      errorsFound: log.result.errors?.length ?? 0,
    };
  }

  /**
   * Format a readable summary of validation results
   */
  formatSummary(): string {
    if (this.logs.length === 0) {
      return 'No validation logs recorded.';
    }

    const lines: string[] = ['Validation Summary:', '-------------------'];

    for (const log of this.logs) {
      const errorCount = log.result.errors?.length ?? 0;
      const status = log.result.isValid ? 'PASS' : 'FAIL';
      lines.push(`  ${log.validatorName}: ${status} (${log.durationMs}ms, ${errorCount} errors)`);
    }

    lines.push('-------------------');
    lines.push(`Total: ${this.getTotalDuration()}ms, ${this.getErrorCount()} errors`);

    return lines.join('\n');
  }
}
