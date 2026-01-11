/**
 * Validation Reporter
 *
 * Formats validation results for human-readable output.
 * Supports text and JSON output formats for CLI and API use.
 *
 * @module engine/validator/validation-reporter
 * @see Issue #348
 */

import type {
  ValidationResult,
  BatchValidationResult,
  ValidationIssue,
} from './types.js';

// ============================================================
// Types
// ============================================================

/**
 * Reporter output options
 */
export interface ReporterOptions {
  /** Only output errors (hide warnings and info) */
  quiet?: boolean;
  /** Use colors in output (default: true if TTY) */
  colors?: boolean;
}

// ============================================================
// Validation Reporter
// ============================================================

/**
 * Formats validation results for display.
 */
export class ValidationReporter {
  /**
   * Print a single validation result
   * @param result - Validation result
   * @param options - Output options
   */
  printResult(
    result: ValidationResult,
    options: ReporterOptions = {}
  ): void {
    const file = result.metadata?.file || 'workflow';

    if (result.valid) {
      if (!options.quiet) {
        console.log(`[PASS] ${file}: Valid`);
      }
      return;
    }

    console.log(`[FAIL] ${file}: Invalid`);

    for (const issue of result.issues) {
      // Skip non-errors in quiet mode
      if (options.quiet && issue.severity !== 'error') {
        continue;
      }

      const icon = this.getIcon(issue.severity);
      const pathInfo = issue.path ? ` (${issue.path})` : '';

      console.log(`  ${icon} [${issue.code}] ${issue.message}${pathInfo}`);

      if (issue.suggestion && !options.quiet) {
        console.log(`     -> ${issue.suggestion}`);
      }
    }

    console.log('');
    console.log(
      `Summary: ${result.summary.errors} errors, ${result.summary.warnings} warnings`
    );
  }

  /**
   * Print batch validation results
   * @param result - Batch validation result
   * @param options - Output options
   */
  printBatchResult(
    result: BatchValidationResult,
    options: ReporterOptions = {}
  ): void {
    console.log('='.repeat(60));
    console.log('Workflow Validation Report');
    console.log('='.repeat(60));
    console.log('');

    for (const [file, fileResult] of result.results) {
      this.printResult(
        { ...fileResult, metadata: { ...fileResult.metadata, file, duration_ms: fileResult.metadata?.duration_ms || 0, level: fileResult.metadata?.level || 1 } },
        options
      );
      console.log('');
    }

    console.log('='.repeat(60));
    console.log('Summary');
    console.log(`  Total files: ${result.summary.total_files}`);
    console.log(`  Valid: ${result.summary.valid_files}`);
    console.log(`  Invalid: ${result.summary.invalid_files}`);
    console.log(`  Errors: ${result.summary.total_errors}`);
    console.log(`  Warnings: ${result.summary.total_warnings}`);
    console.log('='.repeat(60));
  }

  /**
   * Format result as JSON string
   * @param result - Validation result
   * @param pretty - Use pretty printing
   * @returns JSON string
   */
  formatJson(result: ValidationResult, pretty: boolean = true): string {
    return JSON.stringify(result, null, pretty ? 2 : undefined);
  }

  /**
   * Format batch result as JSON string
   * @param result - Batch validation result
   * @param pretty - Use pretty printing
   * @returns JSON string
   */
  formatBatchJson(result: BatchValidationResult, pretty: boolean = true): string {
    // Convert Map to object for JSON serialization
    const serializable = {
      results: Object.fromEntries(result.results),
      summary: result.summary,
    };

    return JSON.stringify(serializable, null, pretty ? 2 : undefined);
  }

  /**
   * Format agent summary for LLM prompt inclusion
   * @param result - Validation result with agent summary
   * @returns Formatted string for LLM prompt
   */
  formatAgentPrompt(result: ValidationResult): string {
    if (result.valid || !result.agentSummary) {
      return '';
    }

    const lines: string[] = [];
    lines.push('## Validation Errors - Please Fix:\n');

    // Fix required list
    for (const fix of result.agentSummary.fixRequired) {
      lines.push(`- ${fix}`);
    }

    // Regeneration hints
    if (result.agentSummary.regenerationHints?.length) {
      lines.push('\n## Regeneration Hints:');
      for (const hint of result.agentSummary.regenerationHints) {
        lines.push(`- ${hint}`);
      }
    }

    return lines.join('\n');
  }

  /**
   * Get icon for severity level
   * @param severity - Issue severity
   * @returns Icon string
   */
  private getIcon(severity: string): string {
    switch (severity) {
      case 'error':
        return '[ERROR]';
      case 'warning':
        return '[WARN]';
      case 'info':
        return '[INFO]';
      default:
        return '[?]';
    }
  }
}

// ============================================================
// Exported Instance
// ============================================================

/**
 * Default validation reporter instance
 */
export const validationReporter = new ValidationReporter();
