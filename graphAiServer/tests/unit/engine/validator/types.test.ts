/**
 * Tests for Workflow Validator Types
 *
 * @module tests/unit/engine/validator/types
 * @see Issue #348
 */

import type {
  ValidationSeverity,
  AgentFeedback,
  ValidationIssue,
  ValidationResult,
  BatchValidationResult,
} from '../../../../src/engine/validator/types.js';

describe('Workflow Validator Types', () => {
  describe('ValidationSeverity', () => {
    it('should accept error severity', () => {
      const severity: ValidationSeverity = 'error';
      expect(severity).toBe('error');
    });

    it('should accept warning severity', () => {
      const severity: ValidationSeverity = 'warning';
      expect(severity).toBe('warning');
    });

    it('should accept info severity', () => {
      const severity: ValidationSeverity = 'info';
      expect(severity).toBe('info');
    });
  });

  describe('AgentFeedback', () => {
    it('should create valid agent feedback with all fields', () => {
      const feedback: AgentFeedback = {
        targetPath: 'steps[0].config.url',
        category: 'schema',
        currentValue: 'http://invalid',
        expectedFormat: 'https://...',
        allowedValues: ['https://api.example.com'],
        fixExample: '"https://api.example.com/v1/users"',
        docUrl: 'https://docs.example.com/url-format',
      };

      expect(feedback.targetPath).toBe('steps[0].config.url');
      expect(feedback.category).toBe('schema');
      expect(feedback.currentValue).toBe('http://invalid');
    });

    it('should create minimal agent feedback', () => {
      const feedback: AgentFeedback = {
        targetPath: 'root',
        category: 'reference',
      };

      expect(feedback.targetPath).toBe('root');
      expect(feedback.category).toBe('reference');
      expect(feedback.currentValue).toBeUndefined();
    });

    it('should support all category types', () => {
      const categories: AgentFeedback['category'][] = ['schema', 'reference', 'type', 'constraint'];

      categories.forEach((category) => {
        const feedback: AgentFeedback = {
          targetPath: 'test',
          category,
        };
        expect(feedback.category).toBe(category);
      });
    });
  });

  describe('ValidationIssue', () => {
    it('should create complete validation issue', () => {
      const issue: ValidationIssue = {
        severity: 'error',
        code: 'UNDEFINED_STEP_REFERENCE',
        message: 'Reference to undefined step: unknown_step',
        path: 'steps[1].params.data',
        line: 45,
        suggestion: 'Check that the step ID exists',
        agentFeedback: {
          targetPath: 'steps[1].params.data',
          category: 'reference',
          currentValue: '${unknown_step.output.result}',
          allowedValues: ['step1', 'step2'],
        },
      };

      expect(issue.severity).toBe('error');
      expect(issue.code).toBe('UNDEFINED_STEP_REFERENCE');
      expect(issue.agentFeedback?.allowedValues).toContain('step1');
    });

    it('should create minimal validation issue', () => {
      const issue: ValidationIssue = {
        severity: 'warning',
        code: 'DEPRECATED_FIELD',
        message: 'Field is deprecated',
      };

      expect(issue.path).toBeUndefined();
      expect(issue.agentFeedback).toBeUndefined();
    });
  });

  describe('ValidationResult', () => {
    it('should create valid result with no issues', () => {
      const result: ValidationResult = {
        valid: true,
        issues: [],
        summary: {
          errors: 0,
          warnings: 0,
          infos: 0,
        },
      };

      expect(result.valid).toBe(true);
      expect(result.issues).toHaveLength(0);
      expect(result.summary.errors).toBe(0);
    });

    it('should create invalid result with issues', () => {
      const result: ValidationResult = {
        valid: false,
        issues: [
          {
            severity: 'error',
            code: 'INVALID_JSON',
            message: 'Invalid JSON syntax',
          },
        ],
        summary: {
          errors: 1,
          warnings: 0,
          infos: 0,
        },
        metadata: {
          file: 'workflow.json',
          duration_ms: 15,
          level: 2,
        },
      };

      expect(result.valid).toBe(false);
      expect(result.issues).toHaveLength(1);
      expect(result.metadata?.level).toBe(2);
    });

    it('should include agentSummary for LLM feedback', () => {
      const result: ValidationResult = {
        valid: false,
        issues: [],
        summary: { errors: 2, warnings: 1, infos: 0 },
        agentSummary: {
          fixRequired: [
            '[SCHEMA_VIOLATION] steps[0].type: Invalid node type',
            '[UNDEFINED_STEP_REFERENCE] output.result: Unknown step reference',
          ],
          suggestedFixes: {
            'steps[0].type': 'api_rest',
          },
          regenerationHints: [
            'steps[0].type: Use one of [api_rest, transform, code_js]',
          ],
        },
      };

      expect(result.agentSummary?.fixRequired).toHaveLength(2);
      expect(result.agentSummary?.suggestedFixes?.['steps[0].type']).toBe('api_rest');
    });
  });

  describe('BatchValidationResult', () => {
    it('should create batch validation result', () => {
      const result: BatchValidationResult = {
        results: new Map([
          ['workflow1.json', {
            valid: true,
            issues: [],
            summary: { errors: 0, warnings: 0, infos: 0 },
          }],
          ['workflow2.json', {
            valid: false,
            issues: [{ severity: 'error', code: 'ERR', message: 'Error' }],
            summary: { errors: 1, warnings: 0, infos: 0 },
          }],
        ]),
        summary: {
          total_files: 2,
          valid_files: 1,
          invalid_files: 1,
          total_errors: 1,
          total_warnings: 0,
        },
      };

      expect(result.summary.total_files).toBe(2);
      expect(result.summary.valid_files).toBe(1);
      expect(result.results.size).toBe(2);
    });
  });
});
