/**
 * Security Configuration - Security defaults and validation
 *
 * This module provides security configuration management for mySwiftAgentCore,
 * including startup validation of required environment variables.
 */

import { z } from 'zod';
import { ErrorCodes, createCoreError, type CoreError } from '../shared/types/error.types.js';

/**
 * Required environment variables for security
 */
export const REQUIRED_SECURITY_ENV_VARS = [
  'API_TOKEN',
  'ADMIN_TOKEN',
  'MYVAULT_SERVICE_TOKEN',
] as const;

/**
 * Security defaults configuration
 */
export const SECURITY_DEFAULTS = {
  /** Token expiration time in seconds (1 hour) */
  tokenExpirationSeconds: 3600,

  /** Maximum request body size in bytes (10MB) */
  maxRequestBodySize: 10 * 1024 * 1024,

  /** Rate limit requests per minute */
  rateLimitPerMinute: 100,

  /** Enable CORS */
  corsEnabled: true,

  /** CORS allowed origins (empty = allow all) */
  corsAllowedOrigins: [] as string[],

  /** Enable request logging */
  requestLoggingEnabled: true,

  /** Sensitive headers to redact in logs */
  sensitiveHeaders: ['authorization', 'x-api-token', 'cookie'],

  /** Enable security headers (Helmet defaults) */
  securityHeadersEnabled: true,
} as const;

/**
 * Security configuration schema
 */
export const SecurityConfigSchema = z.object({
  apiToken: z.string().min(1, 'API_TOKEN is required'),
  adminToken: z.string().min(1, 'ADMIN_TOKEN is required'),
  myvaultServiceToken: z.string().min(1, 'MYVAULT_SERVICE_TOKEN is required'),
  tokenExpirationSeconds: z.number().positive().default(SECURITY_DEFAULTS.tokenExpirationSeconds),
  maxRequestBodySize: z.number().positive().default(SECURITY_DEFAULTS.maxRequestBodySize),
  rateLimitPerMinute: z.number().positive().default(SECURITY_DEFAULTS.rateLimitPerMinute),
  corsEnabled: z.boolean().default(SECURITY_DEFAULTS.corsEnabled),
  corsAllowedOrigins: z.array(z.string()).default([]),
  requestLoggingEnabled: z.boolean().default(SECURITY_DEFAULTS.requestLoggingEnabled),
  securityHeadersEnabled: z.boolean().default(SECURITY_DEFAULTS.securityHeadersEnabled),
});

export type SecurityConfig = z.infer<typeof SecurityConfigSchema>;

/**
 * Security validation result
 */
export interface SecurityValidationResult {
  valid: boolean;
  config?: SecurityConfig;
  errors: CoreError[];
  warnings: string[];
}

/**
 * Validate security configuration from environment variables
 *
 * This function should be called at application startup to ensure
 * all required security settings are properly configured.
 *
 * @returns SecurityValidationResult with config if valid, or errors if not
 */
export function validateSecurityConfig(): SecurityValidationResult {
  const errors: CoreError[] = [];
  const warnings: string[] = [];

  // Collect environment variables
  const envValues = {
    apiToken: process.env['API_TOKEN'],
    adminToken: process.env['ADMIN_TOKEN'],
    myvaultServiceToken: process.env['MYVAULT_SERVICE_TOKEN'],
    tokenExpirationSeconds: parseIntEnv('TOKEN_EXPIRATION_SECONDS'),
    maxRequestBodySize: parseIntEnv('MAX_REQUEST_BODY_SIZE'),
    rateLimitPerMinute: parseIntEnv('RATE_LIMIT_PER_MINUTE'),
    corsEnabled: parseBoolEnv('CORS_ENABLED'),
    corsAllowedOrigins: parseArrayEnv('CORS_ALLOWED_ORIGINS'),
    requestLoggingEnabled: parseBoolEnv('REQUEST_LOGGING_ENABLED'),
    securityHeadersEnabled: parseBoolEnv('SECURITY_HEADERS_ENABLED'),
  };

  // Mapping from env var names to property names
  const envToPropertyMap: Record<string, keyof typeof envValues> = {
    API_TOKEN: 'apiToken',
    ADMIN_TOKEN: 'adminToken',
    MYVAULT_SERVICE_TOKEN: 'myvaultServiceToken',
  };

  // Check for missing required variables
  for (const varName of REQUIRED_SECURITY_ENV_VARS) {
    const propertyName = envToPropertyMap[varName];
    const value = propertyName ? envValues[propertyName] : undefined;
    if (!value || (typeof value === 'string' && value.trim() === '')) {
      errors.push(
        createCoreError(
          ErrorCodes.CFG_MISSING_REQUIRED,
          `Required environment variable ${varName} is not set`,
          'configuration',
          'critical',
          { variableName: varName }
        )
      );
    }
  }

  // If there are critical errors, return early
  if (errors.length > 0) {
    return { valid: false, errors, warnings };
  }

  // Validate with Zod schema
  const result = SecurityConfigSchema.safeParse(envValues);

  if (!result.success) {
    for (const error of result.error.errors) {
      errors.push(
        createCoreError(ErrorCodes.CFG_INVALID_VALUE, error.message, 'configuration', 'high', {
          path: error.path.join('.'),
          code: error.code,
        })
      );
    }
    return { valid: false, errors, warnings };
  }

  // Add warnings for insecure configurations
  if (result.data.corsAllowedOrigins.length === 0) {
    warnings.push(
      'CORS is enabled but no allowed origins are specified. All origins will be allowed.'
    );
  }

  if (!result.data.securityHeadersEnabled) {
    warnings.push(
      'Security headers are disabled. This may expose the application to security vulnerabilities.'
    );
  }

  return {
    valid: true,
    config: result.data,
    errors: [],
    warnings,
  };
}

/**
 * Get security configuration (throws if invalid)
 */
export function getSecurityConfig(): SecurityConfig {
  const result = validateSecurityConfig();
  if (!result.valid || !result.config) {
    const errorMessages = result.errors.map((e) => e.message).join(', ');
    throw new Error(`Security configuration is invalid: ${errorMessages}`);
  }
  return result.config;
}

/**
 * Check if all required security environment variables are set
 */
export function isSecurityConfigured(): boolean {
  return REQUIRED_SECURITY_ENV_VARS.every((varName) => {
    const value = process.env[varName];
    return value !== undefined && value.trim() !== '';
  });
}

/**
 * Get list of missing required environment variables
 */
export function getMissingSecurityEnvVars(): string[] {
  return REQUIRED_SECURITY_ENV_VARS.filter((varName) => {
    const value = process.env[varName];
    return value === undefined || value.trim() === '';
  });
}

// Helper functions

function parseIntEnv(name: string): number | undefined {
  const value = process.env[name];
  if (value === undefined) return undefined;
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? undefined : parsed;
}

function parseBoolEnv(name: string): boolean | undefined {
  const value = process.env[name];
  if (value === undefined) return undefined;
  return value.toLowerCase() === 'true';
}

function parseArrayEnv(name: string): string[] {
  const value = process.env[name];
  if (value === undefined || value.trim() === '') return [];
  return value.split(',').map((s) => s.trim());
}
