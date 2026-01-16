/**
 * Security Configuration for SecurityValidator
 *
 * Issue #369: Context-aware security validation configuration
 *
 * This file centralizes all security-related configuration for better
 * maintainability, testability, and extensibility.
 */

/**
 * Validation context types for security checks
 */
export enum ValidationContextType {
  SHELL_EXECUTION = 'SHELL_EXECUTION',
  JAVASCRIPT_SANDBOX = 'JAVASCRIPT_SANDBOX',
  TEMPLATE_ENGINE = 'TEMPLATE_ENGINE',
  DATA_REFERENCE = 'DATA_REFERENCE',
}

/**
 * Pattern definition for security checks
 */
export interface SecurityPattern {
  pattern: RegExp;
  code: string;
  message: string;
}

/**
 * Security metrics collected during validation
 */
export interface SecurityMetrics {
  totalStepsChecked: number;
  shellContextCount: number;
  jsContextCount: number;
  templateContextCount: number;
  patternsDetected: Record<string, number>;
  validationDurationMs: number;
}

/**
 * Step types that indicate shell execution context
 * Using Set for O(1) lookup performance
 */
export const SHELL_STEP_TYPES = new Set<string>([
  'shell',
  'exec',
  'bash',
  'cmd',
  'system',
  'spawn',
]);

/**
 * Field path patterns that indicate shell context within code_js steps
 * More comprehensive pattern matching than simple string includes
 */
export const SHELL_FIELD_PATTERNS: RegExp[] = [
  /\.shell(?:$|\.)/,
  /\.exec(?:$|\.)/,
  /\.command(?:$|\.)/,
  /\.cmd(?:$|\.)/,
  /\.system_call(?:$|\.)/,
  /\.spawn(?:$|\.)/,
  /\.subprocess(?:$|\.)/,
];

/**
 * Shell context patterns - applied only in shell execution context
 * These patterns detect potential shell injection vulnerabilities
 */
export const SHELL_CONTEXT_PATTERNS: SecurityPattern[] = [
  {
    pattern: /`[^`]*`/,
    code: 'SHELL_INJECTION',
    message: 'Potential shell injection detected (backticks)',
  },
  {
    pattern: /\$\([^)]*\)/,
    code: 'COMMAND_SUBSTITUTION',
    message: 'Potential command substitution detected',
  },
  {
    pattern: /\|\s*\w+/,
    code: 'PIPE_COMMAND',
    message: 'Potential pipe command detected',
  },
  {
    pattern: /;\s*\w+/,
    code: 'COMMAND_CHAIN',
    message: 'Potential command chaining detected',
  },
];

/**
 * General dangerous patterns - applied in all contexts
 * These patterns detect common security vulnerabilities
 */
export const GENERAL_DANGEROUS_PATTERNS: SecurityPattern[] = [
  // SQL injection patterns
  {
    pattern: /['"].*OR.*['"].*=.*['"]/i,
    code: 'SQL_INJECTION',
    message: 'Potential SQL injection pattern detected',
  },
  {
    pattern: /--.*$/m,
    code: 'SQL_COMMENT',
    message: 'SQL comment detected',
  },
  {
    pattern: /;\s*DROP\s+/i,
    code: 'SQL_DROP',
    message: 'Potential SQL DROP statement detected',
  },

  // Path traversal
  {
    pattern: /\.\.\//,
    code: 'PATH_TRAVERSAL',
    message: 'Potential path traversal detected',
  },
  {
    pattern: /\.\.\\/,
    code: 'PATH_TRAVERSAL',
    message: 'Potential path traversal detected (Windows)',
  },
];

/**
 * Sensitive data patterns - generate warnings, not errors
 */
export const SENSITIVE_DATA_PATTERNS: SecurityPattern[] = [
  {
    pattern: /password/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential sensitive data reference (password)',
  },
  {
    pattern: /secret/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential sensitive data reference (secret)',
  },
  {
    pattern: /api[_-]?key/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential API key reference',
  },
  {
    pattern: /private[_-]?key/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential private key reference',
  },
  {
    pattern: /access[_-]?token/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential access token reference',
  },
  {
    pattern: /bearer\s+/i,
    code: 'SENSITIVE_DATA',
    message: 'Potential bearer token reference',
  },
];

/**
 * Dangerous JavaScript patterns - applied in JavaScript context
 */
export const DANGEROUS_JS_PATTERNS: SecurityPattern[] = [
  { pattern: /eval\s*\(/, code: 'EVAL_USAGE', message: 'eval() usage detected' },
  {
    pattern: /Function\s*\(/,
    code: 'FUNCTION_CONSTRUCTOR',
    message: 'Function constructor usage detected',
  },
  {
    pattern: /require\s*\(/,
    code: 'REQUIRE_USAGE',
    message: 'require() usage detected',
  },
  {
    pattern: /import\s*\(/,
    code: 'DYNAMIC_IMPORT',
    message: 'dynamic import usage detected',
  },
  { pattern: /process\./, code: 'PROCESS_ACCESS', message: 'process access detected' },
  { pattern: /__dirname/, code: 'DIRNAME_ACCESS', message: '__dirname access detected' },
  {
    pattern: /child_process/,
    code: 'CHILD_PROCESS',
    message: 'child_process module reference detected',
  },
  { pattern: /fs\./, code: 'FS_ACCESS', message: 'filesystem access detected' },
];

/**
 * Safe domains for API calls (used in api_rest validation)
 */
export const SAFE_DOMAINS: string[] = [
  'localhost',
  '127.0.0.1',
  '*.internal',
  '*.local',
  '*.test',
];

/**
 * Security validation configuration options
 */
export interface SecurityValidatorConfig {
  /** Enable debug logging */
  debug: boolean;
  /** Collect metrics during validation */
  collectMetrics: boolean;
  /** Custom shell step types (merged with defaults) */
  additionalShellStepTypes?: string[];
  /** Custom shell field patterns (merged with defaults) */
  additionalShellFieldPatterns?: RegExp[];
  /** Custom safe domains (merged with defaults) */
  additionalSafeDomains?: string[];
}

/**
 * Default security validator configuration
 */
export const DEFAULT_SECURITY_CONFIG: SecurityValidatorConfig = {
  debug: false,
  collectMetrics: false,
};

/**
 * Create a customized security configuration
 */
export function createSecurityConfig(
  overrides: Partial<SecurityValidatorConfig> = {}
): SecurityValidatorConfig {
  return {
    ...DEFAULT_SECURITY_CONFIG,
    ...overrides,
  };
}

/**
 * Get all shell step types (default + additional)
 */
export function getShellStepTypes(config: SecurityValidatorConfig): Set<string> {
  const types = new Set(SHELL_STEP_TYPES);
  if (config.additionalShellStepTypes) {
    for (const type of config.additionalShellStepTypes) {
      types.add(type);
    }
  }
  return types;
}

/**
 * Get all shell field patterns (default + additional)
 */
export function getShellFieldPatterns(config: SecurityValidatorConfig): RegExp[] {
  const patterns = [...SHELL_FIELD_PATTERNS];
  if (config.additionalShellFieldPatterns) {
    patterns.push(...config.additionalShellFieldPatterns);
  }
  return patterns;
}

/**
 * Get all safe domains (default + additional)
 */
export function getSafeDomains(config: SecurityValidatorConfig): string[] {
  const domains = [...SAFE_DOMAINS];
  if (config.additionalSafeDomains) {
    domains.push(...config.additionalSafeDomains);
  }
  return domains;
}
