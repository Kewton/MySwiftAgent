/**
 * SecurityValidator - Security checks for generated workflows
 *
 * Issue #364: Security validation
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Dangerous patterns to check for
 */
const DANGEROUS_PATTERNS = [
  // Shell injection
  { pattern: /`.*`/, code: 'SHELL_INJECTION', message: 'Potential shell injection detected' },
  { pattern: /\$\(.*\)/, code: 'COMMAND_SUBSTITUTION', message: 'Potential command substitution detected' },

  // SQL injection patterns
  { pattern: /['"].*OR.*['"].*=.*['"]/i, code: 'SQL_INJECTION', message: 'Potential SQL injection pattern detected' },
  { pattern: /--.*$/, code: 'SQL_COMMENT', message: 'SQL comment detected' },

  // Path traversal
  { pattern: /\.\.\//, code: 'PATH_TRAVERSAL', message: 'Potential path traversal detected' },

  // Sensitive data patterns
  { pattern: /password/i, code: 'SENSITIVE_DATA', message: 'Potential sensitive data reference' },
  { pattern: /secret/i, code: 'SENSITIVE_DATA', message: 'Potential sensitive data reference' },
  { pattern: /api[_-]?key/i, code: 'SENSITIVE_DATA', message: 'Potential API key reference' },
  { pattern: /private[_-]?key/i, code: 'SENSITIVE_DATA', message: 'Potential private key reference' },
];

/**
 * Safe domains for API calls
 */
const SAFE_DOMAINS = [
  'localhost',
  '127.0.0.1',
  '*.internal',
];

/**
 * SecurityValidator - Checks for security issues
 *
 * Checks:
 * - Dangerous patterns in code/expressions
 * - External URL validation
 * - Sensitive data exposure
 * - Unsafe JavaScript patterns
 */
export class SecurityValidator implements Validator {
  readonly name = 'SecurityValidator';

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Check each step
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (!step) continue;

      // Check based on step type
      switch (step.type) {
        case 'code_js':
          this.validateCodeJsStep(step, i, errors, warnings);
          break;
        case 'api_rest':
          this.validateApiRestStep(step, i, errors, warnings);
          break;
        case 'transform':
          this.validateTransformStep(step, i, errors, warnings);
          break;
      }

      // Check all string values for dangerous patterns
      this.checkDangerousPatterns(step, i, errors, warnings);
    }

    return {
      isValid: errors.filter((e) => !e.code.startsWith('SENSITIVE')).length === 0,
      errors,
      warnings,
    };
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
    const dangerousPatterns = [
      { pattern: /eval\s*\(/, message: 'eval() usage detected' },
      { pattern: /Function\s*\(/, message: 'Function constructor usage detected' },
      { pattern: /require\s*\(/, message: 'require() usage detected' },
      { pattern: /import\s*\(/, message: 'dynamic import usage detected' },
      { pattern: /process\./, message: 'process access detected' },
      { pattern: /__dirname/, message: '__dirname access detected' },
      { pattern: /child_process/, message: 'child_process module reference detected' },
      { pattern: /fs\./, message: 'filesystem access detected' },
    ];

    for (const { pattern, message } of dangerousPatterns) {
      if (pattern.test(code)) {
        errors.push({
          code: 'UNSAFE_CODE',
          message: `Step "${step.id}": ${message}`,
          path: `steps[${stepIndex}].config.code`,
        });
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
      }

      // Check for localhost in production warning
      if (parsedUrl.hostname === 'localhost' || parsedUrl.hostname === '127.0.0.1') {
        warnings.push({
          code: 'LOCALHOST_URL',
          message: `Step "${step.id}" uses localhost URL - ensure this is intentional`,
        });
      }
    } catch {
      // URL parsing failed - might be a template, skip validation
    }
  }

  /**
   * Validate transform step
   */
  private validateTransformStep(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    _warnings: ValidationWarning[]
  ): void {
    const expression = step.config['expression'] as string | undefined;

    if (!expression) return;

    // Check for dangerous patterns in expressions
    const dangerousPatterns = [
      { pattern: /eval\s*\(/, message: 'eval() in expression' },
      { pattern: /Function\s*\(/, message: 'Function constructor in expression' },
    ];

    for (const { pattern, message } of dangerousPatterns) {
      if (pattern.test(expression)) {
        errors.push({
          code: 'UNSAFE_EXPRESSION',
          message: `Step "${step.id}": ${message}`,
          path: `steps[${stepIndex}].config.expression`,
        });
      }
    }
  }

  /**
   * Check for dangerous patterns in all string values
   */
  private checkDangerousPatterns(
    step: TaskFlowStep,
    stepIndex: number,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const checkObject = (obj: unknown, path: string): void => {
      if (typeof obj === 'string') {
        for (const { pattern, code, message } of DANGEROUS_PATTERNS) {
          if (pattern.test(obj)) {
            // Sensitive data warnings, others are errors
            if (code === 'SENSITIVE_DATA') {
              warnings.push({ code, message: `${message} at ${path}` });
            } else {
              errors.push({ code, message: `${message} at ${path}`, path });
            }
          }
        }
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
   * Check if domain is considered safe
   */
  private isSafeDomain(hostname: string): boolean {
    for (const safe of SAFE_DOMAINS) {
      if (safe.startsWith('*')) {
        const suffix = safe.slice(1);
        if (hostname.endsWith(suffix)) return true;
      } else if (hostname === safe) {
        return true;
      }
    }
    return false;
  }
}
