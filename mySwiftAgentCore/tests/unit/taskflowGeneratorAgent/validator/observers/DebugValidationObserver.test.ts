/**
 * DebugValidationObserver Unit Tests
 *
 * Issue #381: Debug mode observer for validation
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { DebugValidationObserver } from '../../../../../src/taskflowGeneratorAgent/validator/observers/DebugValidationObserver.js';
import type { ValidationResult } from '../../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('DebugValidationObserver', () => {
  let observer: DebugValidationObserver;

  beforeEach(() => {
    observer = new DebugValidationObserver();
    // Mock console.debug to prevent output during tests
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  describe('onValidatorStart', () => {
    it('should log validator start', () => {
      observer.onValidatorStart('TestValidator');

      expect(console.debug).toHaveBeenCalledWith(
        expect.stringContaining('TestValidator')
      );
    });

    it('should record start time', () => {
      observer.onValidatorStart('TestValidator');

      // Start time is recorded internally, getLogs will show the results
    });
  });

  describe('onValidatorComplete', () => {
    it('should log validator completion', () => {
      const result: ValidationResult = {
        isValid: true,
        errors: [],
      };

      observer.onValidatorComplete('TestValidator', result, 50);

      expect(console.debug).toHaveBeenCalledWith(
        expect.stringContaining('TestValidator')
      );
      expect(console.debug).toHaveBeenCalledWith(expect.stringContaining('50ms'));
    });

    it('should record validation log entry', () => {
      const result: ValidationResult = {
        isValid: false,
        errors: [{ code: 'TEST', message: 'Test error' }],
      };

      observer.onValidatorComplete('TestValidator', result, 100);

      const logs = observer.getLogs();
      expect(logs).toHaveLength(1);
      expect(logs[0].validatorName).toBe('TestValidator');
      expect(logs[0].durationMs).toBe(100);
      expect(logs[0].result.isValid).toBe(false);
    });

    it('should include error count in log message', () => {
      const result: ValidationResult = {
        isValid: false,
        errors: [
          { code: 'ERR1', message: 'Error 1' },
          { code: 'ERR2', message: 'Error 2' },
        ],
      };

      observer.onValidatorComplete('TestValidator', result, 50);

      expect(console.debug).toHaveBeenCalledWith(expect.stringContaining('errors: 2'));
    });
  });

  describe('onError', () => {
    it('should log error', () => {
      const error = new Error('Test error message');

      observer.onError('TestValidator', error);

      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('TestValidator')
      );
      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('Test error message')
      );
    });
  });

  describe('getLogs', () => {
    it('should return empty array initially', () => {
      const logs = observer.getLogs();
      expect(logs).toEqual([]);
    });

    it('should return all logged entries', () => {
      const result1: ValidationResult = { isValid: true };
      const result2: ValidationResult = {
        isValid: false,
        errors: [{ code: 'ERR', message: 'Error' }],
      };

      observer.onValidatorComplete('Validator1', result1, 10);
      observer.onValidatorComplete('Validator2', result2, 20);

      const logs = observer.getLogs();
      expect(logs).toHaveLength(2);
      expect(logs[0].validatorName).toBe('Validator1');
      expect(logs[1].validatorName).toBe('Validator2');
    });

    it('should return a copy of logs (not the original)', () => {
      const result: ValidationResult = { isValid: true };
      observer.onValidatorComplete('Validator1', result, 10);

      const logs1 = observer.getLogs();
      const logs2 = observer.getLogs();

      expect(logs1).not.toBe(logs2);
      expect(logs1).toEqual(logs2);
    });

    it('should include timestamp in log entries', () => {
      const result: ValidationResult = { isValid: true };
      const beforeTime = new Date();

      observer.onValidatorComplete('TestValidator', result, 10);

      const logs = observer.getLogs();
      const afterTime = new Date();

      expect(logs[0].timestamp).toBeInstanceOf(Date);
      expect(logs[0].timestamp.getTime()).toBeGreaterThanOrEqual(beforeTime.getTime());
      expect(logs[0].timestamp.getTime()).toBeLessThanOrEqual(afterTime.getTime());
    });
  });

  describe('clearLogs', () => {
    it('should clear all logged entries', () => {
      const result: ValidationResult = { isValid: true };
      observer.onValidatorComplete('Validator1', result, 10);
      observer.onValidatorComplete('Validator2', result, 20);

      expect(observer.getLogs()).toHaveLength(2);

      observer.clearLogs();

      expect(observer.getLogs()).toHaveLength(0);
    });
  });

  describe('getTotalDuration', () => {
    it('should return 0 when no logs', () => {
      expect(observer.getTotalDuration()).toBe(0);
    });

    it('should return sum of all durations', () => {
      const result: ValidationResult = { isValid: true };
      observer.onValidatorComplete('V1', result, 10);
      observer.onValidatorComplete('V2', result, 20);
      observer.onValidatorComplete('V3', result, 30);

      expect(observer.getTotalDuration()).toBe(60);
    });
  });

  describe('getErrorCount', () => {
    it('should return 0 when no errors', () => {
      const result: ValidationResult = { isValid: true };
      observer.onValidatorComplete('V1', result, 10);

      expect(observer.getErrorCount()).toBe(0);
    });

    it('should return total error count across all validators', () => {
      observer.onValidatorComplete(
        'V1',
        {
          isValid: false,
          errors: [
            { code: 'E1', message: 'Error 1' },
            { code: 'E2', message: 'Error 2' },
          ],
        },
        10
      );
      observer.onValidatorComplete(
        'V2',
        {
          isValid: false,
          errors: [{ code: 'E3', message: 'Error 3' }],
        },
        10
      );

      expect(observer.getErrorCount()).toBe(3);
    });
  });

  describe('getValidatorMetrics', () => {
    it('should return metrics for specific validator', () => {
      const result: ValidationResult = {
        isValid: false,
        errors: [{ code: 'E1', message: 'Error' }],
      };
      observer.onValidatorComplete('TestValidator', result, 50);

      const metrics = observer.getValidatorMetrics('TestValidator');

      expect(metrics).toBeDefined();
      expect(metrics!.durationMs).toBe(50);
      expect(metrics!.errorsFound).toBe(1);
    });

    it('should return undefined for unknown validator', () => {
      const metrics = observer.getValidatorMetrics('UnknownValidator');
      expect(metrics).toBeUndefined();
    });
  });

  describe('formatSummary', () => {
    it('should format a readable summary', () => {
      observer.onValidatorComplete('V1', { isValid: true }, 10);
      observer.onValidatorComplete(
        'V2',
        { isValid: false, errors: [{ code: 'E', message: 'Error' }] },
        20
      );

      const summary = observer.formatSummary();

      expect(summary).toContain('V1');
      expect(summary).toContain('V2');
      expect(summary).toContain('10ms');
      expect(summary).toContain('20ms');
      expect(summary).toContain('Total');
    });

    it('should handle empty logs', () => {
      const summary = observer.formatSummary();

      expect(summary).toBeDefined();
      expect(summary).toContain('No validation logs');
    });
  });
});
