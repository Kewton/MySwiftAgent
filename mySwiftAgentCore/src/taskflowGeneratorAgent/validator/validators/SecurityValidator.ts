/**
 * SecurityValidator - Context-aware security checks for generated workflows
 *
 * Issue #364: Security validation
 * Issue #369: Context-aware backtick detection (fixes false positives for JS template literals)
 *
 * Improvements:
 * - Context-aware validation (shell vs JavaScript vs template)
 * - Externalized configuration for better testability
 * - Metrics collection for monitoring
 * - Debug logging for troubleshooting
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import {
  type SecurityPattern,
  type SecurityMetrics,
  type SecurityValidatorConfig,
  ValidationContextType,
  SHELL_CONTEXT_PATTERNS,
  GENERAL_DANGEROUS_PATTERNS,
  SENSITIVE_DATA_PATTERNS,
  DANGEROUS_JS_PATTERNS,
  DEFAULT_SECURITY_CONFIG,
  getShellStepTypes,
  getShellFieldPatterns,
  getSafeDomains,
} from './security-config.js';

/**
 * SecurityValidator - Checks for security issues with context awareness
 *
 * Validation Strategy:
 * 1. Determine the execution context (shell, JavaScript, template)
 * 2. Apply appropriate patterns based on context
 * 3. Collect metrics for monitoring
 *
 * Context Types:
 * - SHELL_EXECUTION: Strict validation (backticks, $(), pipes, etc.)
 * - JAVASCRIPT_SANDBOX: eval/Function restrictions only
 * - TEMPLATE_ENGINE: Minimal restrictions
 * - DATA_REFERENCE: General dangerous patterns only
 */
export class SecurityValidator implements Validator {
  readonly name = 'SecurityValidator';

  private readonly config: SecurityValidatorConfig;
  private readonly shellStepTypes: Set<string>;
  private readonly shellFieldPatterns: RegExp[];
  private readonly safeDomains: string[];
  private metrics: SecurityMetrics | null = null;

  constructor(config: Partial<SecurityValidatorConfig> = {}) {
    this.config = { ...DEFAULT_SECURITY_CONFIG, ...config };
    this.shellStepTypes = getShellStepTypes(this.config);
    this.shellFieldPatterns = getShellFieldPatterns(this.config);
    this.safeDomains = getSafeDomains(this.config);
  }

  /**
   * Get the last validation metrics (if collectMetrics was enabled)
   */
  getMetrics(): SecurityMetrics | null {
    return this.metrics;
  }

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const startTime = Date.now();
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Initialize metrics if enabled
    if (this.config.collectMetrics) {
      this.metrics = {
        totalStepsChecked: 0,
        shellContextCount: 0,
        jsContextCount: 0,
        templateContextCount: 0,
        patternsDetected: {},
        validationDurationMs: 0,
      };
    }

    // Check each step
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (!step) continue;

      if (this.config.collectMetrics && this.metrics) {
        this.metrics.totalStepsChecked++;
      }

      this.debugLog(`Validating step ${step.id} (type: ${step.type})`);

      // Check based on step type
      switch (step.type) {
        case 'code_js':
          this.validateCodeJsStep(step, i, errors, warnings);
          if (this.config.collectMetrics && this.metrics) {
            this.metrics.jsContextCount++;
          }
          break;
        case 'api_rest':
          this.validateApiRestStep(step, i, errors, warnings);
          break;
        case 'transform':
          this.validateTransformStep(step, i, errors, warnings);
          if (this.config.collectMetrics && this.metrics) {
            this.metrics.templateContextCount++;
          }
          break;
      }

      // Check all string values for dangerous patterns
      this.checkDangerousPatterns(step, i, errors, warnings);
    }

    // Finalize metrics
    if (this.config.collectMetrics && this.metrics) {
      this.metrics.validationDurationMs = Date.now() - startTime;
      this.debugLog(`Validation completed in ${this.metrics.validationDurationMs}ms`);
      this.debugLog(`Metrics: ${JSON.stringify(this.metrics)}`);
    }

    return {
      isValid: errors.filter((e) => !e.code.startsWith('SENSITIVE')).length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Determine if the current context is a shell execution context
   *
   * Uses Set and RegExp for robust pattern matching instead of
   * hardcoded string comparisons.
   */
  private isShellContext(step: TaskFlowStep, fieldPath: string): boolean {
    // Check if step type indicates shell execution
    if (this.shellStepTypes.has(step.type)) {
      this.debugLog(`Step ${step.id}: Shell context detected (step type: ${step.type})`);
      return true;
    }

    // For code_js steps, check if the field path indicates shell operations
    if (step.type === 'code_js') {
      for (const pattern of this.shellFieldPatterns) {
        if (pattern.test(fieldPath)) {
          this.debugLog(`Step ${step.id}: Shell context detected (field path: ${fieldPath})`);
          return true;
        }
      }
    }

    // Default to non-shell context (JavaScript/template)
    this.debugLog(`Step ${step.id}: Non-shell context (type: ${step.type}, path: ${fieldPath})`);
    return false;
  }

  /**
   * Determine the validation context type for a step
   */
  private getContextType(step: TaskFlowStep, fieldPath: string): ValidationContextType {
    if (this.isShellContext(step, fieldPath)) {
      return ValidationContextType.SHELL_EXECUTION;
    }

    switch (step.type) {
      case 'code_js':
        return ValidationContextType.JAVASCRIPT_SANDBOX;
      case 'transform':
        return ValidationContextType.TEMPLATE_ENGINE;
      default:
        return ValidationContextType.DATA_REFERENCE;
    }
  }

  /**
   * Validate code_js step
   */
  private validateCodeJsStep(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    _warnings: ValidationWarning[]
  ): void {
    const code = step.config['code'] as string | undefined;

    if (!code) return;

    // Check for dangerous JavaScript patterns
    for (const { pattern, code: errorCode, message } of DANGEROUS_JS_PATTERNS) {
      if (pattern.test(code)) {
        errors.push({
          code: 'UNSAFE_CODE',
          message: `Step "${step.id}": ${message}`,
          path: `steps[${stepIndex}].config.code`,
        });
        this.recordPatternDetected(errorCode);
      }
    }
  }

  /**
   * Validate api_rest step
   */
  private validateApiRestStep(
    step: TaskFlowStep,
    _stepIndex: number,
    _errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const url = step.config['url'] as string | undefined;

    if (!url) return;

    // Skip variable references
    if (url.includes('$')) return;

    try {
      const parsedUrl = new URL(url);

      // Check for http (non-https)
      if (parsedUrl.protocol === 'http:' && !this.isSafeDomain(parsedUrl.hostname)) {
        warnings.push({
          code: 'INSECURE_HTTP',
          message: `Step "${step.id}" uses insecure HTTP for external domain`,
        });
        this.recordPatternDetected('INSECURE_HTTP');
      }

      // Check for localhost in production warning
      if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
        warnings.push({
          code: 'LOCALHOST_URL',
          message: `Step "${step.id}" uses localhost URL - ensure this is intentional`,
        });
        this.recordPatternDetected('LOCALHOST_URL');
      }
    } catch {
      // URL parsing failed - might be a template, skip validation
    }
  }

  /**
   * Validate transform step
   *
   * Note: JavaScript template literals (backticks) are ALLOWED in transform steps
   * because they execute in a sandboxed JavaScript context, not a shell.
   * Only eval/Function are restricted.
   */
  private validateTransformStep(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    _warnings: ValidationWarning[]
  ): void {
    const expression = step.config['expression'] as string | undefined;

    if (!expression) return;

    // Only check for eval/Function in transform expressions
    // Backticks (template literals) are ALLOWED here
    const dangerousPatterns = [
      { pattern: /eval\s*\(/, code: 'EVAL_USAGE', message: 'eval() in expression' },
      {
        pattern: /Function\s*\(/,
        code: 'FUNCTION_CONSTRUCTOR',
        message: 'Function constructor in expression',
      },
    ];

    for (const { pattern, code, message } of dangerousPatterns) {
      if (pattern.test(expression)) {
        errors.push({
          code: 'UNSAFE_EXPRESSION',
          message: `Step "${step.id}": ${message}`,
          path: `steps[${stepIndex}].config.expression`,
        });
        this.recordPatternDetected(code);
      }
    }
  }

  /**
   * Check for dangerous patterns in all string values
   *
   * Context-aware: Shell injection patterns are only checked in shell context
   */
  private checkDangerousPatterns(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const checkObject = (obj: unknown, path: string): void => {
      if (typeof obj === 'string') {
        const contextType = this.getContextType(step, path);

        // Apply shell-specific patterns only in shell context
        if (contextType === ValidationContextType.SHELL_EXECUTION) {
          this.checkPatterns(obj, path, SHELL_CONTEXT_PATTERNS, errors, warnings, false);
          if (this.config.collectMetrics && this.metrics) {
            this.metrics.shellContextCount++;
          }
        }

        // Apply general dangerous patterns based on context
        // Skip SQL-related patterns for JavaScript/code context (they don't apply to JS code)
        if (contextType === ValidationContextType.JAVASCRIPT_SANDBOX) {
          // Filter out SQL-related patterns for JavaScript context
          const jsApplicablePatterns = GENERAL_DANGEROUS_PATTERNS.filter(
            (p) => !p.code.startsWith('SQL_')
          );
          this.checkPatterns(obj, path, jsApplicablePatterns, errors, warnings, false);
        } else {
          // Apply all general dangerous patterns in other contexts
          this.checkPatterns(obj, path, GENERAL_DANGEROUS_PATTERNS, errors, warnings, false);
        }

        // Apply sensitive data patterns (warnings only)
        this.checkPatterns(obj, path, SENSITIVE_DATA_PATTERNS, errors, warnings, true);
      } else if (Array.isArray(obj)) {
        obj.forEach((item, i) => checkObject(item, `${path}[${i}]`));
      } else if (obj && typeof obj === 'object') {
        for (const [key, value] of Object.entries(obj)) {
          checkObject(value, `${path}.${key}`);
        }
      }
    };

    checkObject(step.config, `steps[${stepIndex}].config`);
    checkObject(step.params, `steps[${stepIndex}].params`);
  }

  /**
   * Check a value against a list of patterns
   */
  private checkPatterns(
    value: string,
    path: string,
    patterns: SecurityPattern[],
    errors: ValidationError[],
    warnings: ValidationWarning[],
    warningOnly: boolean
  ): void {
    for (const { pattern, code, message } of patterns) {
      if (pattern.test(value)) {
        if (warningOnly) {
          warnings.push({ code, message: `${message} at ${path}` });
        } else {
          errors.push({ code, message: `${message} at ${path}`, path });
        }
        this.recordPatternDetected(code);
      }
    }
  }

  /**
   * Check if domain is considered safe
   */
  private isSafeDomain(hostname: string): boolean {
    for (const safe of this.safeDomains) {
      if (safe.startsWith('*')) {
        const suffix = safe.slice(1);
        if (hostname.endsWith(suffix)) return true;
      } else if (hostname === safe) {
        return true;
      }
    }
    return false;
  }

  /**
   * Record a detected pattern in metrics
   */
  private recordPatternDetected(code: string): void {
    if (this.config.collectMetrics && this.metrics) {
      this.metrics.patternsDetected[code] = (this.metrics.patternsDetected[code] || 0) + 1;
    }
  }

  /**
   * Debug logging (only when debug mode is enabled)
   */
  private debugLog(message: string): void {
    if (this.config.debug) {
      console.debug(`[SecurityValidator] ${message}`);
    }
  }
}
