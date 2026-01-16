/**
 * SecurityError Unit Tests
 *
 * Issue #363: Security error handling
 */

import { describe, it, expect } from 'vitest';
import {
  SecurityError,
  SecurityErrorCode,
  isSecurityError,
} from '../../../../src/taskflowEngine/sandbox/SecurityError.js';

describe('SecurityError', () => {
  describe('constructor', () => {
    it('should create error with message and code', () => {
      const error = new SecurityError(
        'Script not in whitelist',
        SecurityErrorCode.SCRIPT_NOT_WHITELISTED
      );

      expect(error.message).toBe('Script not in whitelist');
      expect(error.code).toBe(SecurityErrorCode.SCRIPT_NOT_WHITELISTED);
      expect(error.name).toBe('SecurityError');
    });

    it('should create error with context', () => {
      const error = new SecurityError(
        'Script integrity check failed',
        SecurityErrorCode.SCRIPT_INTEGRITY_FAILED,
        { scriptPath: 'test.js', expectedHash: 'abc123' }
      );

      expect(error.context?.scriptPath).toBe('test.js');
      expect(error.context?.expectedHash).toBe('abc123');
    });
  });

  describe('SecurityErrorCode', () => {
    it('should have all expected error codes', () => {
      expect(SecurityErrorCode.SCRIPT_NOT_WHITELISTED).toBe('SCRIPT_NOT_WHITELISTED');
      expect(SecurityErrorCode.SCRIPT_INTEGRITY_FAILED).toBe('SCRIPT_INTEGRITY_FAILED');
      expect(SecurityErrorCode.FUNCTION_NOT_FOUND).toBe('FUNCTION_NOT_FOUND');
      expect(SecurityErrorCode.EXECUTION_TIMEOUT).toBe('EXECUTION_TIMEOUT');
      expect(SecurityErrorCode.MEMORY_LIMIT_EXCEEDED).toBe('MEMORY_LIMIT_EXCEEDED');
      expect(SecurityErrorCode.PATH_TRAVERSAL_DETECTED).toBe('PATH_TRAVERSAL_DETECTED');
    });
  });

  describe('isSecurityError', () => {
    it('should return true for SecurityError instances', () => {
      const error = new SecurityError('test', SecurityErrorCode.SCRIPT_NOT_WHITELISTED);
      expect(isSecurityError(error)).toBe(true);
    });

    it('should return false for regular Error', () => {
      const error = new Error('test');
      expect(isSecurityError(error)).toBe(false);
    });

    it('should return false for non-error values', () => {
      expect(isSecurityError(null)).toBe(false);
      expect(isSecurityError(undefined)).toBe(false);
      expect(isSecurityError('string')).toBe(false);
      expect(isSecurityError(123)).toBe(false);
    });
  });

  describe('instanceof', () => {
    it('should be instanceof Error', () => {
      const error = new SecurityError('test', SecurityErrorCode.SCRIPT_NOT_WHITELISTED);
      expect(error instanceof Error).toBe(true);
    });

    it('should be instanceof SecurityError', () => {
      const error = new SecurityError('test', SecurityErrorCode.SCRIPT_NOT_WHITELISTED);
      expect(error instanceof SecurityError).toBe(true);
    });
  });
});
