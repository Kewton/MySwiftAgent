/**
 * WorkflowCapabilityValidator Unit Tests
 *
 * Issue #374: Capability-aware workflow validation
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  WorkflowCapabilityValidator,
  createWorkflowCapabilityValidator,
} from '../../../../src/taskflowGeneratorAgent/validator/WorkflowCapabilityValidator.js';
import type { ValidationContext } from '../../../../src/taskflowGeneratorAgent/validator/ValidationPipeline.js';
import type { TaskFlowDefinition } from '../../../../src/taskflowEngine/types/TaskFlowDefinition.js';
import type { CapabilityForPrompt } from '../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('WorkflowCapabilityValidator', () => {
  let validator: WorkflowCapabilityValidator;

  beforeEach(() => {
    validator = new WorkflowCapabilityValidator();
  });

  describe('constructor and metadata', () => {
    it('should have name property', () => {
      expect(validator.name).toBe('WorkflowCapabilityValidator');
    });

    it('should be created via factory function', () => {
      const v = createWorkflowCapabilityValidator();
      expect(v).toBeInstanceOf(WorkflowCapabilityValidator);
    });
  });

  describe('validateRequiredParams', () => {
    it('should detect missing required parameters', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                // Missing required 'queries' parameter
                num: 5,
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
            { name: 'num', type: 'number', required: false },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors).toBeDefined();
      expect(result.errors?.some(e => e.code === 'MISSING_REQUIRED_PARAM')).toBe(true);
      expect(result.errors?.some(e => e.message.includes('queries'))).toBe(true);
    });

    it('should pass when all required parameters are present', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['test query'],
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('validateParamTypes', () => {
    it('should detect type mismatch', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['test'],
                num: 'five', // Should be number, not string
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
            { name: 'num', type: 'number', required: false },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors?.some(e => e.code === 'PARAM_TYPE_MISMATCH')).toBe(true);
      expect(result.errors?.some(e => e.message.includes('num'))).toBe(true);
    });

    it('should skip type check for dynamic references', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: '$input.search_terms', // Dynamic reference
                num: '$steps.previous.count', // Dynamic reference
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
            { name: 'num', type: 'number', required: false },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });

    it('should correctly identify array type', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['query1', 'query2'],
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });
  });

  describe('validateParamConstraints', () => {
    it('should detect value below minimum', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['test'],
                num: 0, // Below minimum of 1
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
            {
              name: 'num',
              type: 'number',
              required: false,
              validation: { min: 1, max: 100 },
            },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors?.some(e => e.code === 'PARAM_BELOW_MIN')).toBe(true);
    });

    it('should detect value above maximum', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['test'],
                num: 200, // Above maximum of 100
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
            {
              name: 'num',
              type: 'number',
              required: false,
              validation: { min: 1, max: 100 },
            },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors?.some(e => e.code === 'PARAM_ABOVE_MAX')).toBe(true);
    });

    it('should detect value not in enum', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'email_step',
            type: 'api_rest',
            config: { capability_id: 'email_api' },
            params: {
              body: {
                to: 'test@example.com',
                priority: 'urgent', // Not in enum ['low', 'normal', 'high']
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'email_api',
          name: 'Email API',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'to', type: 'string', required: true },
            {
              name: 'priority',
              type: 'string',
              required: false,
              validation: { enum: ['low', 'normal', 'high'] },
            },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors?.some(e => e.code === 'PARAM_NOT_IN_ENUM')).toBe(true);
    });

    it('should pass when value is in enum', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'email_step',
            type: 'api_rest',
            config: { capability_id: 'email_api' },
            params: {
              body: {
                to: 'test@example.com',
                priority: 'high',
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'email_api',
          name: 'Email API',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'to', type: 'string', required: true },
            {
              name: 'priority',
              type: 'string',
              required: false,
              validation: { enum: ['low', 'normal', 'high'] },
            },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });
  });

  describe('warnUnknownParams', () => {
    it('should warn about unknown parameters', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                queries: ['test'],
                unknownParam: 'value', // Unknown parameter
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      // Unknown params are warnings, not errors
      expect(result.isValid).toBe(true);
      expect(result.warnings?.some(w => w.code === 'UNKNOWN_PARAM')).toBe(true);
      expect(result.warnings?.some(w => w.message.includes('unknownParam'))).toBe(true);
    });
  });

  describe('multiple validation errors', () => {
    it('should collect all errors from multiple steps', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'step_1',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: {
              body: {
                // Missing required 'queries'
              },
            },
          },
          {
            id: 'step_2',
            type: 'api_rest',
            config: { capability_id: 'email_api' },
            params: {
              body: {
                // Missing required 'to'
              },
            },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
        {
          id: 'email_api',
          name: 'Email API',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'to', type: 'string', required: true },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(false);
      expect(result.errors?.length).toBeGreaterThanOrEqual(2);
    });
  });

  describe('non-capability steps', () => {
    it('should skip validation for non-api_rest steps', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'transform_step',
            type: 'transform',
            config: {},
            params: { data: '$input.data' },
          },
          {
            id: 'llm_step',
            type: 'llm',
            config: {},
            params: { prompt: 'Generate text' },
          },
        ],
        output: {},
      };

      const context: ValidationContext = {
        capabilities: [],
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      expect(result.isValid).toBe(true);
    });
  });

  describe('suggestion generation', () => {
    it('should provide suggestion for missing required param', async () => {
      const workflow: TaskFlowDefinition = {
        workflow_name: 'test_workflow',
        input_schema: { type: 'object' },
        output_schema: { type: 'object' },
        steps: [
          {
            id: 'search_step',
            type: 'api_rest',
            config: { capability_id: 'google_search' },
            params: { body: {} },
          },
        ],
        output: {},
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
      ];

      const context: ValidationContext = {
        capabilities: capabilities as any,
        projectId: 'test-project',
      };

      const result = await validator.validate(workflow, context);

      // Should have suggestion in error
      const error = result.errors?.find(e => e.code === 'MISSING_REQUIRED_PARAM');
      expect(error).toBeDefined();
      // Error message should provide guidance
      expect(error?.message).toContain('queries');
    });
  });
});
