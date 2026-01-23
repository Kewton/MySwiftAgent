/**
 * Secrets Injection Integration Tests
 *
 * Issue #377: End-to-end tests for unified secrets injection
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { SecretAnalyzer } from '../../../src/taskflowEngine/analyzer/SecretAnalyzer.js';
import { SecretNotFoundError } from '../../../src/taskflowEngine/errors/SecretNotFoundError.js';
import { createDefaultNodeRegistry } from '../../../src/taskflowEngine/nodes/index.js';
import type { InternalWorkflowDefinition } from '../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';
import type { SecretManager } from '../../../src/shared/context/SecretManager.js';

describe('Secrets Injection Integration', () => {
  let analyzer: SecretAnalyzer;

  beforeEach(() => {
    vi.clearAllMocks();
    const registry = createDefaultNodeRegistry();
    analyzer = new SecretAnalyzer(registry);
  });

  describe('SecretAnalyzer with real node registry', () => {
    it('should analyze workflow with LLM node', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_llm_test',
        name: 'LLM Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'llm_step',
            name: 'Generate Summary',
            type: 'llm',
            config: {
              prompt: 'Summarize: {{input.text}}',
              model: 'gpt-4',
            },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: { summary: 'llm_step.output' },
      };

      const result = await analyzer.analyze(workflow);

      expect(result.workflowId).toBe('wf_llm_test');
      // Issue #396: LlmNode only requires OPENAI_API_KEY (LLM_API_KEY is optional fallback)
      expect(result.requiredSecrets).toContain('OPENAI_API_KEY');
      expect(result.requiredSecrets).not.toContain('LLM_API_KEY');
    });

    it('should analyze workflow with API node using auth', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_api_test',
        name: 'API Test Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'api_step',
            name: 'Fetch Data',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com/data',
              method: 'GET',
              auth: {
                type: 'bearer',
                secret_key: 'EXAMPLE_API_KEY',
              },
            },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: { data: 'api_step.output' },
      };

      const result = await analyzer.analyze(workflow);

      expect(result.workflowId).toBe('wf_api_test');
      expect(result.requiredSecrets).toContain('EXAMPLE_API_KEY');
    });

    it('should analyze complex workflow with multiple secret-requiring nodes', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_complex',
        name: 'Complex Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'fetch_step',
            name: 'Fetch Data',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com/data',
              method: 'GET',
              auth: {
                type: 'bearer',
                secret_key: 'DATA_API_KEY',
              },
            },
            params: {},
          },
          {
            id: 'transform_step',
            name: 'Transform Data',
            type: 'transform',
            config: { transform: 'return input;' },
            params: {},
          },
          {
            id: 'llm_step',
            name: 'Analyze Data',
            type: 'llm',
            config: {
              prompt: 'Analyze: {{steps.fetch_step.output}}',
            },
            params: {},
          },
          {
            id: 'post_step',
            name: 'Post Results',
            type: 'api_rest',
            config: {
              url: 'https://api.example.com/results',
              method: 'POST',
              auth: {
                type: 'api_key',
                secret_key: 'RESULTS_API_KEY',
                header_name: 'X-API-Key',
              },
            },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: { result: 'post_step.output' },
      };

      const result = await analyzer.analyze(workflow);

      // Should collect all unique secrets
      // Issue #396: LLM_API_KEY is no longer in requiredSecrets (optional fallback)
      expect(result.requiredSecrets).toContain('DATA_API_KEY');
      expect(result.requiredSecrets).toContain('OPENAI_API_KEY');
      expect(result.requiredSecrets).not.toContain('LLM_API_KEY');
      expect(result.requiredSecrets).toContain('RESULTS_API_KEY');

      // Should track by step
      expect(result.byStep['fetch_step']).toContain('DATA_API_KEY');
      expect(result.byStep['llm_step']).toContain('OPENAI_API_KEY');
      expect(result.byStep['post_step']).toContain('RESULTS_API_KEY');
      expect(result.byStep).not.toHaveProperty('transform_step');
    });

    it('should handle workflow with no secret requirements', async () => {
      const workflow: InternalWorkflowDefinition = {
        id: 'wf_no_secrets',
        name: 'No Secrets Workflow',
        version: '1.0.0',
        steps: [
          {
            id: 'transform_step',
            name: 'Transform Data',
            type: 'transform',
            config: { transform: 'return { processed: input };' },
            params: {},
          },
        ],
        inputSchema: { type: 'object' },
        outputSchema: { type: 'object' },
        outputMapping: { result: 'transform_step.output' },
      };

      const result = await analyzer.analyze(workflow);

      expect(result.requiredSecrets).toEqual([]);
      expect(Object.keys(result.byStep)).toHaveLength(0);
    });
  });

  describe('SecretNotFoundError integration', () => {
    it('should create meaningful error message with full context', () => {
      const error = new SecretNotFoundError('OPENAI_API_KEY', {
        workflowId: 'wf_test',
        stepId: 'llm_step',
        nodeType: 'llm',
      });

      expect(error.message).toContain('OPENAI_API_KEY');
      expect(error.message).toContain('wf_test');
      expect(error.message).toContain('llm_step');
      expect(error.message).toContain('llm');
    });

    it('should serialize error to JSON for API responses', () => {
      const error = new SecretNotFoundError('API_KEY', {
        workflowId: 'wf_test',
        stepId: 'step_1',
      });

      const json = error.toJSON();

      expect(json).toHaveProperty('code', 'SECRET_NOT_FOUND');
      expect(json).toHaveProperty('secretKey', 'API_KEY');
      expect(json).toHaveProperty('workflowId', 'wf_test');
      expect(json).toHaveProperty('stepId', 'step_1');
    });
  });

  describe('Selective secret fetching simulation', () => {
    it('should demonstrate selective secret fetching pattern', async () => {
      // Simulate the handler pattern with selective fetching
      const mockSecretManager: SecretManager = {
        get: vi.fn().mockImplementation((key: string) => {
          const secrets: Record<string, string> = {
            OPENAI_API_KEY: 'sk-openai-key',
            LLM_API_KEY: 'sk-llm-key',
            DATA_API_KEY: 'data-key',
          };
          return Promise.resolve(secrets[key]);
        }),
        clearCache: vi.fn(),
        isMyVaultEnabled: vi.fn().mockReturnValue(false),
        getMyVaultBaseUrl: vi.fn(),
      } as unknown as SecretManager;

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_selective',
        name: 'Selective Fetch Workflow',
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

      // Analyze to get required secrets
      const requirements = await analyzer.analyze(workflow);

      // Fetch only required secrets
      const secrets: Record<string, string> = {};
      for (const key of requirements.requiredSecrets) {
        const value = await mockSecretManager.get(key);
        if (value) {
          secrets[key] = value;
        }
      }

      // Verify only required secrets were fetched
      expect(mockSecretManager.get).toHaveBeenCalledWith('OPENAI_API_KEY');
      expect(mockSecretManager.get).toHaveBeenCalledWith('LLM_API_KEY');
      // DATA_API_KEY should NOT be fetched since workflow doesn't need it
      expect(mockSecretManager.get).not.toHaveBeenCalledWith('DATA_API_KEY');

      // Verify secrets object has correct values
      expect(secrets['OPENAI_API_KEY']).toBe('sk-openai-key');
      expect(secrets['LLM_API_KEY']).toBe('sk-llm-key');
    });

    it('should throw SecretNotFoundError for missing required secrets', async () => {
      const mockSecretManager: SecretManager = {
        get: vi.fn().mockResolvedValue(undefined), // All secrets missing
        clearCache: vi.fn(),
        isMyVaultEnabled: vi.fn().mockReturnValue(false),
        getMyVaultBaseUrl: vi.fn(),
      } as unknown as SecretManager;

      const workflow: InternalWorkflowDefinition = {
        id: 'wf_missing_secrets',
        name: 'Missing Secrets Workflow',
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

      const requirements = await analyzer.analyze(workflow);
      const missingSecrets: string[] = [];

      for (const key of requirements.requiredSecrets) {
        const value = await mockSecretManager.get(key);
        if (!value) {
          missingSecrets.push(key);
        }
      }

      // All LLM secrets should be missing
      expect(missingSecrets).toContain('OPENAI_API_KEY');
      expect(missingSecrets).toContain('LLM_API_KEY');

      // Create appropriate error
      if (missingSecrets.length > 0) {
        const error = new SecretNotFoundError(missingSecrets[0], {
          workflowId: workflow.id,
        });
        expect(error.code).toBe('SECRET_NOT_FOUND');
      }
    });
  });
});
