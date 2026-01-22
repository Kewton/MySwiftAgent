/**
 * SecretNotFoundError Unit Tests
 *
 * Issue #377: Unified secrets injection error handling
 */

import { describe, it, expect } from 'vitest';
import {
  SecretNotFoundError,
  isSecretNotFoundError,
} from '../../../../src/taskflowEngine/errors/SecretNotFoundError.js';

describe('SecretNotFoundError', () => {
  describe('constructor', () => {
    it('should create error with secret key', () => {
      const error = new SecretNotFoundError('API_KEY');

      expect(error).toBeInstanceOf(Error);
      expect(error).toBeInstanceOf(SecretNotFoundError);
      expect(error.secretKey).toBe('API_KEY');
      expect(error.message).toContain('API_KEY');
    });

    it('should include workflow context in message', () => {
      const error = new SecretNotFoundError('API_KEY', {
        workflowId: 'wf_test',
      });

      expect(error.workflowId).toBe('wf_test');
      expect(error.message).toContain('wf_test');
    });

    it('should include step context in message', () => {
      const error = new SecretNotFoundError('API_KEY', {
        workflowId: 'wf_test',
        stepId: 'step_1',
      });

      expect(error.stepId).toBe('step_1');
      expect(error.message).toContain('step_1');
    });

    it('should include node type context in message', () => {
      const error = new SecretNotFoundError('API_KEY', {
        workflowId: 'wf_test',
        stepId: 'step_1',
        nodeType: 'llm',
      });

      expect(error.nodeType).toBe('llm');
      expect(error.message).toContain('llm');
    });

    it('should have correct name property', () => {
      const error = new SecretNotFoundError('API_KEY');
      expect(error.name).toBe('SecretNotFoundError');
    });

    it('should have error code', () => {
      const error = new SecretNotFoundError('API_KEY');
      expect(error.code).toBe('SECRET_NOT_FOUND');
    });
  });

  describe('toJSON', () => {
    it('should serialize to JSON with all fields', () => {
      const error = new SecretNotFoundError('API_KEY', {
        workflowId: 'wf_test',
        stepId: 'step_1',
        nodeType: 'llm',
      });

      const json = error.toJSON();

      expect(json).toEqual({
        code: 'SECRET_NOT_FOUND',
        secretKey: 'API_KEY',
        workflowId: 'wf_test',
        stepId: 'step_1',
        nodeType: 'llm',
        message: expect.any(String),
      });
    });

    it('should omit undefined fields', () => {
      const error = new SecretNotFoundError('API_KEY');
      const json = error.toJSON();

      expect(json).not.toHaveProperty('workflowId');
      expect(json).not.toHaveProperty('stepId');
      expect(json).not.toHaveProperty('nodeType');
    });
  });

  describe('getRequiredSecrets', () => {
    it('should return array with single secret key', () => {
      const error = new SecretNotFoundError('API_KEY');
      expect(error.getRequiredSecrets()).toEqual(['API_KEY']);
    });
  });
});

describe('isSecretNotFoundError', () => {
  it('should return true for SecretNotFoundError instances', () => {
    const error = new SecretNotFoundError('API_KEY');
    expect(isSecretNotFoundError(error)).toBe(true);
  });

  it('should return false for regular Error instances', () => {
    const error = new Error('Something went wrong');
    expect(isSecretNotFoundError(error)).toBe(false);
  });

  it('should return false for non-error values', () => {
    expect(isSecretNotFoundError(null)).toBe(false);
    expect(isSecretNotFoundError(undefined)).toBe(false);
    expect(isSecretNotFoundError('error')).toBe(false);
    expect(isSecretNotFoundError({})).toBe(false);
  });
});
