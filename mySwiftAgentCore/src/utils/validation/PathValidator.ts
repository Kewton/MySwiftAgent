/**
 * PathValidator - Secure path validation utility
 *
 * Issue #370: Security validation for file paths
 *
 * Features:
 * - Path traversal attack prevention
 * - Prototype pollution attack prevention
 * - Length validation
 * - Pattern validation
 */

/**
 * Path validation error
 */
export class PathValidationError extends Error {
  readonly path: string;
  readonly reason: string;

  constructor(path: string, reason: string) {
    super(`Invalid path "${path}": ${reason}`);
    this.name = 'PathValidationError';
    this.path = path;
    this.reason = reason;
  }
}

/**
 * Default configuration constants
 */
const DEFAULT_MAX_LENGTH = 128;
const VALID_PATH_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]*$/;

/**
 * Blocked patterns for security
 */
const BLOCKED_PATTERNS = [
  '..',
  '__proto__',
  'constructor',
  'prototype',
  '/',
  '\\',
  '~',
];

/**
 * Path validator configuration
 */
export interface PathValidatorConfig {
  maxLength?: number;
  additionalBlockedPatterns?: string[];
}

/**
 * PathValidator - Validates paths for security
 */
export class PathValidator {
  private readonly maxLength: number;
  private readonly blockedPatterns: string[];

  constructor(config?: PathValidatorConfig) {
    this.maxLength = config?.maxLength ?? DEFAULT_MAX_LENGTH;
    this.blockedPatterns = [
      ...BLOCKED_PATTERNS,
      ...(config?.additionalBlockedPatterns ?? []),
    ];
  }

  /**
   * Validate a path
   *
   * @param path - Path to validate
   * @returns true if valid
   * @throws PathValidationError if invalid
   */
  validate(path: string): boolean {
    // Check empty
    if (!path || path.length === 0) {
      throw new PathValidationError(path, 'Path cannot be empty');
    }

    // Check length
    if (path.length > this.maxLength) {
      throw new PathValidationError(
        path,
        `Path exceeds maximum length of ${this.maxLength} characters`
      );
    }

    // Check blocked patterns
    for (const pattern of this.blockedPatterns) {
      if (path.includes(pattern)) {
        throw new PathValidationError(
          path,
          `Path contains blocked pattern "${pattern}"`
        );
      }
    }

    // Check valid pattern
    if (!VALID_PATH_PATTERN.test(path)) {
      throw new PathValidationError(
        path,
        'Path must start with alphanumeric and contain only alphanumeric, underscore, or hyphen'
      );
    }

    return true;
  }

  /**
   * Sanitize and return validated path
   *
   * @param path - Path to sanitize
   * @returns Validated path
   * @throws PathValidationError if invalid
   */
  sanitize(path: string): string {
    this.validate(path);
    return path;
  }
}

/**
 * Factory function to create PathValidator
 */
export function createPathValidator(config?: PathValidatorConfig): PathValidator {
  return new PathValidator(config);
}
