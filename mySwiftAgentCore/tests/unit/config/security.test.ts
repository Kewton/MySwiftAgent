/**
 * Security Configuration Unit Tests
 *
 * Tests for security validation and configuration
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
  validateSecurityConfig,
  getSecurityConfig,
  isSecurityConfigured,
  getMissingSecurityEnvVars,
  SECURITY_DEFAULTS,
  REQUIRED_SECURITY_ENV_VARS,
} from '../../../src/config/security.js';

// All env vars that might be modified during tests
const ALL_TEST_ENV_VARS = [
  'API_TOKEN',
  'ADMIN_TOKEN',
  'MYVAULT_SERVICE_TOKEN',
  'TOKEN_EXPIRATION_SECONDS',
  'MAX_REQUEST_BODY_SIZE',
  'RATE_LIMIT_PER_MINUTE',
  'CORS_ENABLED',
  'CORS_ALLOWED_ORIGINS',
  'REQUEST_LOGGING_ENABLED',
  'SECURITY_HEADERS_ENABLED',
] as const;

describe('Security Configuration', () => {
  // Store original env vars
  const originalEnv: Record<string, string | undefined> = {};

  beforeEach(() => {
    // Save and clear all test env vars to ensure clean state
    for (const key of ALL_TEST_ENV_VARS) {
      originalEnv[key] = process.env[key];
      delete process.env[key];
    }
  });

  afterEach(() => {
    // Restore all env vars
    for (const key of ALL_TEST_ENV_VARS) {
      if (originalEnv[key] === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = originalEnv[key];
      }
    }
  });

  describe('SECURITY_DEFAULTS', () => {
    it('should have expected default values', () => {
      expect(SECURITY_DEFAULTS.tokenExpirationSeconds).toBe(3600);
      expect(SECURITY_DEFAULTS.maxRequestBodySize).toBe(10 * 1024 * 1024);
      expect(SECURITY_DEFAULTS.rateLimitPerMinute).toBe(100);
      expect(SECURITY_DEFAULTS.corsEnabled).toBe(true);
      expect(SECURITY_DEFAULTS.sensitiveHeaders).toContain('authorization');
    });
  });

  describe('REQUIRED_SECURITY_ENV_VARS', () => {
    it('should list all required environment variables', () => {
      expect(REQUIRED_SECURITY_ENV_VARS).toContain('API_TOKEN');
      expect(REQUIRED_SECURITY_ENV_VARS).toContain('ADMIN_TOKEN');
      expect(REQUIRED_SECURITY_ENV_VARS).toContain('MYVAULT_SERVICE_TOKEN');
    });
  });

  describe('validateSecurityConfig', () => {
    it('should return invalid when required vars are missing', () => {
      const result = validateSecurityConfig();
      expect(result.valid).toBe(false);
      expect(result.errors.length).toBe(REQUIRED_SECURITY_ENV_VARS.length);
    });

    it('should return valid when all required vars are set', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const result = validateSecurityConfig();
      expect(result.valid).toBe(true);
      expect(result.errors.length).toBe(0);
      expect(result.config).toBeDefined();
    });

    it('should include config when valid', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const result = validateSecurityConfig();
      expect(result.config?.apiToken).toBe('test-api-token');
      expect(result.config?.adminToken).toBe('test-admin-token');
    });

    it('should add warning when CORS origins not specified', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const result = validateSecurityConfig();
      expect(result.warnings.some((w) => w.includes('CORS'))).toBe(true);
    });

    it('should add warning when security headers disabled', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';
      process.env['SECURITY_HEADERS_ENABLED'] = 'false';

      const result = validateSecurityConfig();
      expect(result.warnings.some((w) => w.includes('Security headers'))).toBe(true);
    });

    it('should parse optional numeric values', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';
      process.env['TOKEN_EXPIRATION_SECONDS'] = '7200';

      const result = validateSecurityConfig();
      expect(result.config?.tokenExpirationSeconds).toBe(7200);
    });

    it('should parse optional boolean values', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';
      process.env['CORS_ENABLED'] = 'false';

      const result = validateSecurityConfig();
      expect(result.config?.corsEnabled).toBe(false);
    });

    it('should parse CORS allowed origins', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';
      process.env['CORS_ALLOWED_ORIGINS'] = 'http://localhost:3000,http://localhost:8000';

      const result = validateSecurityConfig();
      expect(result.config?.corsAllowedOrigins).toEqual([
        'http://localhost:3000',
        'http://localhost:8000',
      ]);
    });
  });

  describe('getSecurityConfig', () => {
    it('should throw when configuration is invalid', () => {
      expect(() => getSecurityConfig()).toThrow('Security configuration is invalid');
    });

    it('should return config when valid', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const config = getSecurityConfig();
      expect(config.apiToken).toBe('test-api-token');
    });
  });

  describe('isSecurityConfigured', () => {
    it('should return false when vars are missing', () => {
      expect(isSecurityConfigured()).toBe(false);
    });

    it('should return true when all vars are set', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      expect(isSecurityConfigured()).toBe(true);
    });

    it('should return false when any var is empty', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = '';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      expect(isSecurityConfigured()).toBe(false);
    });
  });

  describe('getMissingSecurityEnvVars', () => {
    it('should return all missing vars', () => {
      const missing = getMissingSecurityEnvVars();
      expect(missing.length).toBe(REQUIRED_SECURITY_ENV_VARS.length);
      expect(missing).toContain('API_TOKEN');
    });

    it('should return empty array when all vars set', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['ADMIN_TOKEN'] = 'test-admin-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const missing = getMissingSecurityEnvVars();
      expect(missing).toEqual([]);
    });

    it('should identify specific missing vars', () => {
      process.env['API_TOKEN'] = 'test-api-token';
      process.env['MYVAULT_SERVICE_TOKEN'] = 'test-myvault-token';

      const missing = getMissingSecurityEnvVars();
      expect(missing).toContain('ADMIN_TOKEN');
      expect(missing).not.toContain('API_TOKEN');
    });
  });
});
