/**
 * SecretAnalyzer Unit Tests
 *
 * Issue #377: Workflow secret requirements analysis
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  SecretAnalyzer,
  createSecretAnalyzer,
  type WorkflowSecretRequirements,
} from '../../../../src/taskflowEngine/analyzer/SecretAnalyzer.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';
import type { NodeRegistry } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

// Create mock node executors
// Issue #396: LLM_API_KEY is now optional fallback, only OPENAI_API_KEY is required
const createMockLlmExecutor = () => ({
  type: 'llm' as const,
  requiredSecrets: ['OPENAI_API_KEY'] as readonly string[],
  execute: vi.fn(),
  validate: vi.fn().mockReturnValue({ valid: true, errors: [] }),
});

const createMockApiRestExecutor = () => ({
  type: 'api_rest' as const,
  getRequiredSecrets: vi.fn().mockResolvedValue([]),
  execute: vi.fn(),
  validate: vi.fn().mockReturnValue({ valid: true, errors: [] }),
});

const createMockTransformExecutor = () => ({
  type: 'transform' as const,
  execute: vi.fn(),
  validate: vi.fn().mockReturnValue({ valid: true, errors: [] }),
});

describe('SecretAnalyzer', () => {
  let analyzer: SecretAnalyzer;
  let mockRegistry: NodeRegistry;
  let mockLlmExecutor: ReturnType<typeof createMockLlmExecutor>;
  let mockApiRestExecutor: ReturnType<typeof createMockApiRestExecutor>;
  let mockTransformExecutor: ReturnType<typeof createMockTransformExecutor>;

  beforeEach(() => {
    vi.clearAllMocks();

    mockLlmExecutor = createMockLlmExecutor();
    mockApiRestExecutor = createMockApiRestExecutor();
    mockTransformExecutor = createMockTransformExecutor();

    mockRegistry = {
      get: vi.fn((type: string) => {
        switch (type) {
          case 'llm':
            return mockLlmExecutor;
          case 'api_rest':
            return mockApiRestExecutor;
          case 'transform':
            return mockTransformExecutor;
          default:
            return undefined;
        }
      }),
      has: vi.fn((type: string) => ['llm', 'api_rest', 'transform'].includes(type)),
      register: vi.fn(),
      listTypes: vi.fn(),
    } as unknown as NodeRegistry;

    analyzer = new SecretAnalyzer(mockRegistry);
  });

  describe('constructor', () => {
    it('should create instance with registry', () => {
      expect(analyzer).toBeInstanceOf(SecretAnalyzer);
    });
  });

  describe('analyze', () => {
    it('should return empty requirements for workflow with no secret-requiring nodes', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'step_1',
            name: 'Transform Step',
            type: 'transform',
            config: { transform: 'return input;' },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      const result = await analyzer.analyze(workflow);

      expect(result.workflowId).toBe('wf_test');
      expect(result.requiredSecrets).toEqual([]);
      expect(result.byStep).toEqual({});
    });

    it('should collect static secrets from llm node', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'llm_step',
            name: 'LLM Step',
            type: 'llm',
            config: { prompt: 'Hello' },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      const result = await analyzer.analyze(workflow);

      expect(result.requiredSecrets).toContain('OPENAI_API_KEY');
      expect(result.requiredSecrets).toContain('LLM_API_KEY');
      expect(result.byStep['llm_step']).toContain('OPENAI_API_KEY');
      expect(result.byStep['llm_step']).toContain('LLM_API_KEY');
    });

    it('should collect dynamic secrets from api_rest node with auth', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'api_step',
            name: 'API Step',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com',
              method: 'GET',
              auth: {
                type: 'bearer',
                secret_key: 'MY_API_TOKEN',
              },
            },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      mockApiRestExecutor.getRequiredSecrets.mockResolvedValue(['MY_API_TOKEN']);

      const result = await analyzer.analyze(workflow);

      expect(result.requiredSecrets).toContain('MY_API_TOKEN');
      expect(result.byStep['api_step']).toContain('MY_API_TOKEN');
      expect(mockApiRestExecutor.getRequiredSecrets).toHaveBeenCalledWith(
        expect.objectContaining({ config: expect.objectContaining({ auth: expect.any(Object) }) })
      );
    });

    it('should deduplicate secrets across steps', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'llm_step_1',
            name: 'LLM Step 1',
            type: 'llm',
            config: { prompt: 'Hello 1' },
            params: {},
          },
          {
            id: 'llm_step_2',
            name: 'LLM Step 2',
            type: 'llm',
            config: { prompt: 'Hello 2' },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      const result = await analyzer.analyze(workflow);

      // Should only have unique secrets
      const uniqueSecrets = [...new Set(result.requiredSecrets)];
      expect(result.requiredSecrets.length).toBe(uniqueSecrets.length);
    });

    it('should handle mixed node types', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_mixed',
        name: 'Mixed Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'transform_step',
            name: 'Transform Step',
            type: 'transform',
            config: {},
            params: {},
          },
          {
            id: 'llm_step',
            name: 'LLM Step',
            type: 'llm',
            config: { prompt: 'Hello' },
            params: {},
          },
          {
            id: 'api_step',
            name: 'API Step',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com',
              method: 'GET',
              auth: { type: 'bearer', secret_key: 'CUSTOM_TOKEN' },
            },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      mockApiRestExecutor.getRequiredSecrets.mockResolvedValue(['CUSTOM_TOKEN']);

      const result = await analyzer.analyze(workflow);

      expect(result.requiredSecrets).toContain('OPENAI_API_KEY');
      expect(result.requiredSecrets).toContain('LLM_API_KEY');
      expect(result.requiredSecrets).toContain('CUSTOM_TOKEN');
      expect(Object.keys(result.byStep)).toHaveLength(2); // transform has no secrets
    });

    it('should skip unknown node types gracefully', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_test',
        name: 'Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'unknown_step',
            name: 'Unknown Step',
            type: 'unknown_type' as any,
            config: {},
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: {},
      };

      const result = await analyzer.analyze(workflow);

      expect(result.requiredSecrets).toEqual([]);
      expect(result.byStep).toEqual({});
    });
  });

  describe('getStaticSecrets', () => {
    it('should return static secrets from executor with requiredSecrets property', () => {
      const secrets = analyzer.getStaticSecrets(mockLlmExecutor);
      // Issue #396: Only OPENAI_API_KEY is required now
      expect(secrets).toEqual(['OPENAI_API_KEY']);
    });

    it('should return empty array for executor without requiredSecrets', () => {
      const secrets = analyzer.getStaticSecrets(mockTransformExecutor);
      expect(secrets).toEqual([]);
    });
  });

  describe('getDynamicSecrets', () => {
    it('should return dynamic secrets from executor with getRequiredSecrets method', async () => {
      const config = { nodeId: 'api_1', type: 'api_rest', config: { auth: { secret_key: 'TOKEN' } } };
      mockApiRestExecutor.getRequiredSecrets.mockResolvedValue(['TOKEN']);

      const secrets = await analyzer.getDynamicSecrets(mockApiRestExecutor, config);
      expect(secrets).toEqual(['TOKEN']);
    });

    it('should return empty array for executor without getRequiredSecrets', async () => {
      const config = { nodeId: 'transform_1', type: 'transform', config: {} };
      const secrets = await analyzer.getDynamicSecrets(mockTransformExecutor, config);
      expect(secrets).toEqual([]);
    });
  });
});

describe('createSecretAnalyzer factory', () => {
  it('should create a SecretAnalyzer instance', () => {
    const mockRegistry = {
      get: vi.fn(),
      has: vi.fn(),
      register: vi.fn(),
      listTypes: vi.fn(),
    } as unknown as NodeRegistry;

    const analyzer = createSecretAnalyzer(mockRegistry);
    expect(analyzer).toBeInstanceOf(SecretAnalyzer);
  });
});

describe('WorkflowSecretRequirements type', () => {
  it('should have correct structure', () => {
    const requirements: WorkflowSecretRequirements = {
      workflowId: 'wf_test',
      requiredSecrets: ['API_KEY'],
      byStep: {
        step_1: ['API_KEY'],
      },
    };

    expect(requirements.workflowId).toBe('wf_test');
    expect(requirements.requiredSecrets).toContain('API_KEY');
    expect(requirements.byStep['step_1']).toContain('API_KEY');
  });
});
