/**
 * ValidationPipeline Unit Tests
 *
 * Issue #364: Multi-stage validation pipeline for generated workflows
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ValidationPipeline,
  createValidationPipeline,
  type Validator,
  type ValidationContext,
} from '../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import type {
  ValidationResult,
  ValidationError,
  Capability,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';

// Mock validator for testing
class MockValidator implements Validator {
  readonly name: string;
  private readonly errors: ValidationError[];
  private readonly warnings: Array<{ code: string; message: string }>;

  constructor(
    name: string,
    errors: ValidationError[] = [],
    warnings: Array<{ code: string; message: string }> = []
  ) {
    this.name = name;
    this.errors = errors;
    this.warnings = warnings;
  }

  async validate(
    _workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    return {
      isValid: this.errors.length === 0,
      errors: this.errors,
      warnings: this.warnings,
    };
  }
}

describe('ValidationPipeline', () => {
  let pipeline: ValidationPipeline;

  describe('constructor', () => {
    it('should create with default validators', () => {
      pipeline = new ValidationPipeline();

      expect(pipeline.getValidators().length).toBeGreaterThan(0);
    });

    it('should accept custom validators', () => {
      const customValidators = [
        new MockValidator('Custom1'),
        new MockValidator('Custom2'),
      ];

      pipeline = new ValidationPipeline(customValidators);

      expect(pipeline.getValidators()).toHaveLength(2);
    });
  });

  describe('validate', () => {
    const validWorkflow: TaskFlowDefinition = {
      workflow_name: 'test_workflow',
      description: 'Test workflow',
      input_schema: { type: 'object', properties: { input: { type: 'string' } } },
      output_schema: { type: 'object', properties: { output: { type: 'string' } } },
      steps: [
        {
          id: 'step_1',
          type: 'transform',
          config: {},
          params: { data: '$input' },
        },
      ],
      output: { result: '$steps.step_1.data' },
    };

    const context: ValidationContext = {
      capabilities: [],
      projectId: 'test_project',
    };

    it('should return valid for passing workflow', async () => {
      const validators = [new MockValidator('Validator1'), new MockValidator('Validator2')];

      pipeline = new ValidationPipeline(validators);

      const result = await pipeline.validate(validWorkflow, context);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should aggregate errors from multiple validators', async () => {
      const validators = [
        new MockValidator('Validator1', [
          { code: 'ERROR_1', message: 'Error from validator 1' },
        ]),
        new MockValidator('Validator2', [
          { code: 'ERROR_2', message: 'Error from validator 2' },
        ]),
      ];

      pipeline = new ValidationPipeline(validators);

      const result = await pipeline.validate(validWorkflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(2);
      expect(result.errors?.map((e) => e.code)).toContain('ERROR_1');
      expect(result.errors?.map((e) => e.code)).toContain('ERROR_2');
    });

    it('should aggregate warnings from multiple validators', async () => {
      const validators = [
        new MockValidator('Validator1', [], [{ code: 'WARN_1', message: 'Warning 1' }]),
        new MockValidator('Validator2', [], [{ code: 'WARN_2', message: 'Warning 2' }]),
      ];

      pipeline = new ValidationPipeline(validators);

      const result = await pipeline.validate(validWorkflow, context);

      expect(result.isValid).toBe(true);
      expect(result.warnings).toHaveLength(2);
    });

    it('should handle mixed errors and warnings', async () => {
      const validators = [
        new MockValidator(
          'Validator1',
          [{ code: 'ERROR_1', message: 'Error 1' }],
          [{ code: 'WARN_1', message: 'Warning 1' }]
        ),
        new MockValidator('Validator2', [], [{ code: 'WARN_2', message: 'Warning 2' }]),
      ];

      pipeline = new ValidationPipeline(validators);

      const result = await pipeline.validate(validWorkflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.warnings).toHaveLength(2);
    });
  });

  describe('addValidator', () => {
    it('should add validator to pipeline', () => {
      pipeline = new ValidationPipeline([]);

      pipeline.addValidator(new MockValidator('NewValidator'));

      expect(pipeline.getValidators()).toHaveLength(1);
    });
  });

  describe('removeValidator', () => {
    it('should remove validator by name', () => {
      const validators = [
        new MockValidator('Validator1'),
        new MockValidator('Validator2'),
      ];

      pipeline = new ValidationPipeline(validators);
      pipeline.removeValidator('Validator1');

      const remaining = pipeline.getValidators();
      expect(remaining).toHaveLength(1);
      expect(remaining[0].name).toBe('Validator2');
    });
  });
});

describe('createValidationPipeline', () => {
  it('should create ValidationPipeline instance', () => {
    const pipeline = createValidationPipeline();

    expect(pipeline).toBeInstanceOf(ValidationPipeline);
  });

  it('should accept custom validators', () => {
    const validators = [new MockValidator('Custom')];
    const pipeline = createValidationPipeline(validators);

    expect(pipeline.getValidators()).toHaveLength(1);
  });
});
