/**
 * Runtime Validator for TaskFlow Engine
 *
 * Performs Level 3 validation - runtime checks:
 * - URL reachability (optional)
 * - SSL certificate validity
 * - DNS resolution
 *
 * Note: Runtime validation is slower and requires network access.
 * Use sparingly and with appropriate timeouts.
 *
 * @module engine/validator/runtime-validator
 * @see Issue #348
 */

import type {
  ValidationResult,
  ValidationIssue,
  AsyncValidatorLayer,
} from './types.js';

// ============================================================
// Types
// ============================================================

/**
 * Runtime validation options
 */
export interface RuntimeValidatorOptions {
  /** Timeout for network requests in milliseconds */
  timeout_ms?: number;
  /** Whether to check URL reachability */
  checkUrls?: boolean;
}

// ============================================================
// Runtime Validator
// ============================================================

/**
 * Validates runtime aspects of workflow definitions.
 *
 * Level 3 validation includes:
 * - URL reachability checks
 * - SSL certificate validation
 * - DNS resolution
 *
 * Note: This validator makes network requests and can be slow.
 */
export class RuntimeValidator implements AsyncValidatorLayer {
  /**
   * Default timeout for URL checks
   */
  private readonly defaultTimeout = 5000;

  /**
   * Validate a workflow definition's runtime aspects
   * @param definition - Workflow definition object
   * @param options - Validation options
   * @returns Validation result
   */
  async validate(
    definition: unknown,
    options: RuntimeValidatorOptions = {}
  ): Promise<ValidationResult> {
    const issues: ValidationIssue[] = [];
    const timeout = options.timeout_ms || this.defaultTimeout;

    if (!definition || typeof definition !== 'object') {
      return this.buildResult(issues);
    }

    const def = definition as Record<string, unknown>;

    // Only check URLs if explicitly requested
    if (options.checkUrls) {
      const urlIssues = await this.checkUrls(def, timeout);
      issues.push(...urlIssues);
    }

    return this.buildResult(issues);
  }

  /**
   * Check URL reachability for API steps
   */
  private async checkUrls(
    definition: Record<string, unknown>,
    timeout: number
  ): Promise<ValidationIssue[]> {
    const issues: ValidationIssue[] = [];
    const urls = this.extractUrls(definition);

    for (const { url, path } of urls) {
      // Skip variable references
      if (url.includes('${')) {
        continue;
      }

      try {
        const isReachable = await this.checkUrlReachability(url, timeout);

        if (!isReachable) {
          issues.push({
            severity: 'warning',
            code: 'URL_UNREACHABLE',
            message: `URL may not be reachable: ${url}`,
            path,
            suggestion: 'Check the URL is correct and accessible',
            agentFeedback: {
              targetPath: path,
              category: 'constraint',
              currentValue: url,
              expectedFormat: 'A reachable HTTPS URL',
            },
          });
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);

        // Detect SSL errors
        if (message.includes('certificate') || message.includes('SSL')) {
          issues.push({
            severity: 'error',
            code: 'SSL_CERTIFICATE_ERROR',
            message: `SSL certificate error for ${url}: ${message}`,
            path,
            suggestion: 'Check the SSL certificate is valid',
          });
        } else {
          issues.push({
            severity: 'warning',
            code: 'URL_CHECK_FAILED',
            message: `Failed to check URL ${url}: ${message}`,
            path,
          });
        }
      }
    }

    return issues;
  }

  /**
   * Check if a URL is reachable
   */
  private async checkUrlReachability(
    url: string,
    timeout: number
  ): Promise<boolean> {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method: 'HEAD', // Use HEAD to minimize data transfer
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Consider 2xx and 3xx as reachable
      return response.status < 400;
    } catch (error) {
      // Network errors, timeouts, etc.
      if (error instanceof Error && error.name === 'AbortError') {
        return false; // Timeout
      }
      throw error; // Re-throw for SSL/other errors to be handled above
    }
  }

  /**
   * Extract all URLs from workflow definition
   */
  private extractUrls(
    definition: Record<string, unknown>
  ): Array<{ url: string; path: string }> {
    const urls: Array<{ url: string; path: string }> = [];
    const steps = definition.steps as unknown[] | undefined;

    if (!steps) return urls;

    this.walkSteps(steps, (step, path) => {
      const stepObj = step as Record<string, unknown>;

      if (stepObj.type === 'api_rest' && stepObj.config) {
        const config = stepObj.config as Record<string, unknown>;

        if (config.url && typeof config.url === 'string') {
          urls.push({
            url: config.url,
            path: `${path}.config.url`,
          });
        }
      }
    });

    return urls;
  }

  /**
   * Walk all steps recursively
   */
  private walkSteps(
    steps: unknown[],
    callback: (step: unknown, path: string) => void,
    basePath: string = 'steps'
  ): void {
    steps.forEach((step, index) => {
      const currentPath = `${basePath}[${index}]`;
      callback(step, currentPath);

      if (!step || typeof step !== 'object') return;

      const stepObj = step as Record<string, unknown>;

      // Handle parallel blocks
      if (stepObj.type === 'parallel' && Array.isArray(stepObj.steps)) {
        this.walkSteps(stepObj.steps, callback, `${currentPath}.steps`);
      }

      // Handle conditional blocks
      if (stepObj.type === 'conditional') {
        if (Array.isArray(stepObj.then)) {
          this.walkSteps(stepObj.then, callback, `${currentPath}.then`);
        }
        if (Array.isArray(stepObj.else)) {
          this.walkSteps(stepObj.else, callback, `${currentPath}.else`);
        }
      }
    });
  }

  /**
   * Build validation result from issues
   */
  private buildResult(issues: ValidationIssue[]): ValidationResult {
    const errors = issues.filter((i) => i.severity === 'error').length;
    const warnings = issues.filter((i) => i.severity === 'warning').length;
    const infos = issues.filter((i) => i.severity === 'info').length;

    return {
      valid: errors === 0,
      issues,
      summary: { errors, warnings, infos },
    };
  }
}

// ============================================================
// Exported Instance
// ============================================================

/**
 * Default runtime validator instance
 */
export const runtimeValidator = new RuntimeValidator();
