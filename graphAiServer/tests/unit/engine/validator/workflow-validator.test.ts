/**
 * Tests for Workflow Validator
 *
 * @module tests/unit/engine/validator/workflow-validator
 * @see Issue #348
 */

import { WorkflowValidator, type ValidatorOptions } from '../../../../src/engine/validator/workflow-validator.js';
import * as path from 'path';
import * as fs from 'fs/promises';
import * as os from 'os';

describe('WorkflowValidator', () => {
  let validator: WorkflowValidator;
  let tempDir: string;

  beforeAll(async () => {
    // Create temp directory for test files
    tempDir = path.join(os.tmpdir(), 'workflow-validator-test');
    await fs.mkdir(tempDir, { recursive: true });
  });

  afterAll(async () => {
    // Clean up temp directory
    await fs.rm(tempDir, { recursive: true, force: true });
  });

  beforeEach(() => {
    // Create validator with temp directory allowed
    validator = new WorkflowValidator({}, [tempDir]);
  });

  describe('validate', () => {
    it('should validate a correct workflow definition', async () => {
      const definition = {
        workflow_name: 'test_workflow',
        input_schema: { userId: 'string' },
        output_schema: { result: 'string' },
        steps: [
          {
            id: 'fetch_user',
            type: 'api_rest',
            config: {
              method: 'GET',
              url: 'https://api.example.com/users/${inputs.userId}',
            },
          },
        ],
        output: {
          result: '${fetch_user.output.name}',
        },
      };

      const result = await validator.validate(definition);

      expect(result.valid).toBe(true);
      expect(result.summary.errors).toBe(0);
      expect(result.metadata?.level).toBe(2); // Default level
    });

    it('should detect schema violations', async () => {
      const definition = {
        workflow_name: 'test',
        // Missing input_schema, output_schema, steps, output
      };

      const result = await validator.validate(definition);

      expect(result.valid).toBe(false);
      expect(result.summary.errors).toBeGreaterThan(0);
      expect(result.issues.some((i) => i.code.includes('SCHEMA'))).toBe(true);
    });

    it('should detect semantic issues at level 2', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template', template: '${undefined_step.output.data}' },
          },
        ],
        output: { result: '${step1.output.result}' },
      };

      const result = await validator.validate(definition, { level: 2 });

      expect(result.valid).toBe(false);
      expect(result.issues.some((i) => i.code === 'UNDEFINED_STEP_REFERENCE')).toBe(true);
    });

    it('should skip semantic validation at level 1', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template', template: '${undefined_step.output.data}' },
          },
        ],
        output: { result: '${step1.output.result}' },
      };

      const result = await validator.validate(definition, { level: 1 });

      // Should be valid at schema level only
      expect(result.valid).toBe(true);
      expect(result.issues.filter((i) => i.code === 'UNDEFINED_STEP_REFERENCE')).toHaveLength(0);
    });

    it('should include agentSummary when requested', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template', template: '${undefined_step.output.data}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(definition, { includeAgentFeedback: true });

      expect(result.valid).toBe(false);
      expect(result.agentSummary).toBeDefined();
      expect(result.agentSummary?.fixRequired).toBeDefined();
      expect(result.agentSummary?.fixRequired?.length).toBeGreaterThan(0);
    });

    it('should treat warnings as errors in strict mode', async () => {
      // This test depends on having a workflow that generates warnings
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template' },
          },
        ],
        output: {},
      };

      const normalResult = await validator.validate(definition, { strict: false });
      const strictResult = await validator.validate(definition, { strict: true });

      // In strict mode, warnings count toward validity
      if (normalResult.summary.warnings > 0) {
        expect(strictResult.valid).toBe(false);
      }
    });
  });

  describe('validateFile', () => {
    it('should validate a JSON file', async () => {
      const workflowPath = path.join(tempDir, 'valid-workflow.json');
      const workflow = {
        workflow_name: 'file_test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template' },
          },
        ],
        output: {},
      };

      await fs.writeFile(workflowPath, JSON.stringify(workflow));

      const result = await validator.validateFile(workflowPath);

      expect(result.valid).toBe(true);
      expect(result.metadata?.file).toBe(workflowPath);
    });

    it('should detect invalid JSON', async () => {
      const invalidPath = path.join(tempDir, 'invalid.json');
      await fs.writeFile(invalidPath, '{ invalid json }');

      const result = await validator.validateFile(invalidPath);

      expect(result.valid).toBe(false);
      expect(result.issues[0].code).toBe('INVALID_JSON');
      expect(result.issues[0].agentFeedback).toBeDefined();
    });

    it('should block path traversal attacks', async () => {
      // Try to access file outside allowed directory
      const traversalPath = path.join(tempDir, '..', 'etc', 'passwd');

      const result = await validator.validateFile(traversalPath);

      expect(result.valid).toBe(false);
      expect(result.issues[0].code).toBe('PATH_NOT_ALLOWED');
    });

    it('should block absolute paths outside allowed directories', async () => {
      const outsidePath = '/etc/passwd';

      const result = await validator.validateFile(outsidePath);

      expect(result.valid).toBe(false);
      expect(result.issues[0].code).toBe('PATH_NOT_ALLOWED');
    });
  });

  describe('validateDirectory', () => {
    it('should validate all JSON files in a directory', async () => {
      // Create test files
      const workflow1 = {
        workflow_name: 'workflow1',
        input_schema: {},
        output_schema: {},
        steps: [{ id: 's1', type: 'transform', config: { mode: 'template' } }],
        output: {},
      };

      const workflow2 = {
        workflow_name: 'workflow2',
        input_schema: {},
        output_schema: {},
        steps: [{ id: 's1', type: 'transform', config: { mode: 'template' } }],
        output: {},
      };

      const invalidWorkflow = { invalid: 'data' };

      await fs.writeFile(path.join(tempDir, 'w1.json'), JSON.stringify(workflow1));
      await fs.writeFile(path.join(tempDir, 'w2.json'), JSON.stringify(workflow2));
      await fs.writeFile(path.join(tempDir, 'invalid.json'), JSON.stringify(invalidWorkflow));

      const result = await validator.validateDirectory(tempDir);

      expect(result.summary.total_files).toBeGreaterThanOrEqual(3);
      expect(result.summary.valid_files).toBeGreaterThanOrEqual(2);
      expect(result.summary.invalid_files).toBeGreaterThanOrEqual(1);
    });
  });

  describe('dependency injection', () => {
    it('should accept injected validators', async () => {
      // Create mock validators
      const mockSchemaValidator = {
        validate: jest.fn().mockReturnValue({
          valid: true,
          issues: [],
          summary: { errors: 0, warnings: 0, infos: 0 },
        }),
      };

      const mockSemanticValidator = {
        validate: jest.fn().mockReturnValue({
          valid: true,
          issues: [],
          summary: { errors: 0, warnings: 0, infos: 0 },
        }),
      };

      const customValidator = new WorkflowValidator({
        schemaValidator: mockSchemaValidator as any,
        semanticValidator: mockSemanticValidator as any,
      });

      await customValidator.validate({ workflow_name: 'test' });

      expect(mockSchemaValidator.validate).toHaveBeenCalled();
    });
  });

  describe('agentSummary generation', () => {
    it('should generate fixRequired list from errors', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template', template: '${bad_ref.output.x}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(definition, { includeAgentFeedback: true });

      expect(result.agentSummary?.fixRequired).toBeDefined();
      expect(result.agentSummary?.fixRequired?.[0]).toContain('UNDEFINED_STEP_REFERENCE');
    });

    it('should generate regenerationHints from agentFeedback', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'valid_step',
            type: 'transform',
            config: { mode: 'template' },
          },
          {
            id: 'step2',
            type: 'transform',
            config: { mode: 'template', template: '${invalid_ref.output.x}' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(definition, { includeAgentFeedback: true });

      // Should include hint about available steps
      if (result.agentSummary?.regenerationHints) {
        expect(result.agentSummary.regenerationHints.length).toBeGreaterThan(0);
      }
    });

    it('should not include agentSummary when validation passes', async () => {
      const definition = {
        workflow_name: 'test',
        input_schema: {},
        output_schema: {},
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mode: 'template' },
          },
        ],
        output: {},
      };

      const result = await validator.validate(definition, { includeAgentFeedback: true });

      expect(result.valid).toBe(true);
      expect(result.agentSummary).toBeUndefined();
    });
  });
});
