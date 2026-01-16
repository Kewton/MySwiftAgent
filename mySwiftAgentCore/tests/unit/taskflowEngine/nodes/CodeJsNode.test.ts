/**
 * CodeJsNode Unit Tests
 *
 * Issue #363: JavaScript execution node
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  CodeJsNodeExecutor,
  createCodeJsNodeExecutor,
} from '../../../../src/taskflowEngine/nodes/CodeJsNode.js';
import type { NodeConfig, ExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';
import type { CodeJsSandbox } from '../../../../src/taskflowEngine/sandbox/CodeJsSandbox.js';

// Mock sandbox
const mockSandbox: CodeJsSandbox = {
  execute: vi.fn(),
  validateScript: vi.fn(),
};

describe('CodeJsNodeExecutor', () => {
  let executor: CodeJsNodeExecutor;
  let context: ExecutionContext;

  beforeEach(() => {
    vi.clearAllMocks();
    executor = new CodeJsNodeExecutor(mockSandbox);
    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {},
    };
  });

  describe('type', () => {
    it('should have type code_js', () => {
      expect(executor.type).toBe('code_js');
    });
  });

  describe('validate', () => {
    it('should validate config with script', () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script: 'return input.value * 2;',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should validate config with script_ref', () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script_ref: 'scripts/transform.js',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should require script or script_ref', () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {},
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Either script or script_ref is required');
    });
  });

  describe('execute', () => {
    it('should execute inline script via sandbox', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script: 'return input.value * 2;',
        },
      };
      const params = { value: 5 };

      vi.mocked(mockSandbox.execute).mockResolvedValue({
        success: true,
        output: { result: 10 },
        logs: ['Executed successfully'],
      });

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ result: 10 });
      expect(mockSandbox.execute).toHaveBeenCalledWith(
        'return input.value * 2;',
        expect.objectContaining({
          input: params,
          context: expect.any(Object),
        }),
        expect.objectContaining({ timeout: expect.any(Number) })
      );
    });

    it('should handle sandbox execution failure', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script: 'throw new Error("test error");',
        },
      };

      vi.mocked(mockSandbox.execute).mockResolvedValue({
        success: false,
        error: {
          code: 'SCRIPT_ERROR',
          message: 'test error',
        },
      });

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('SCRIPT_ERROR');
    });

    it('should pass context variables to sandbox', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script: 'return { env: context.env };',
        },
      };
      context.variables = { env: 'production' };

      vi.mocked(mockSandbox.execute).mockResolvedValue({
        success: true,
        output: { env: 'production' },
      });

      await executor.execute(config, {}, context);

      expect(mockSandbox.execute).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          context: expect.objectContaining({
            variables: { env: 'production' },
          }),
        }),
        expect.any(Object)
      );
    });

    it('should handle missing configuration', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {},
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('CODE_JS_ERROR');
    });

    it('should handle script_ref execution', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script_ref: 'scripts/transform.js',
        },
      };

      vi.mocked(mockSandbox.execute).mockResolvedValue({
        success: true,
        output: { processed: true },
      });

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(true);
      expect(mockSandbox.execute).toHaveBeenCalled();
    });

    it('should apply timeout from config', async () => {
      const config: NodeConfig = {
        nodeId: 'code_1',
        type: 'code_js',
        config: {
          script: 'return 1;',
          timeout: 5000,
        },
      };

      vi.mocked(mockSandbox.execute).mockResolvedValue({
        success: true,
        output: 1,
      });

      await executor.execute(config, {}, context);

      expect(mockSandbox.execute).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({ timeout: 5000 })
      );
    });
  });
});

describe('createCodeJsNodeExecutor factory', () => {
  it('should create a CodeJsNodeExecutor instance', () => {
    const executor = createCodeJsNodeExecutor(mockSandbox);
    expect(executor).toBeInstanceOf(CodeJsNodeExecutor);
  });
});
