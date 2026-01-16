/**
 * BaseNode Unit Tests
 *
 * Issue #363: Node executor interface and base implementation
 */

import { describe, it, expect } from 'vitest';
import {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  ExecutionContext,
  ValidationResult,
  createNodeExecutor,
  NodeRegistry,
  createNodeRegistry,
} from '../../../../src/taskflowEngine/nodes/BaseNode.js';

describe('NodeExecutor Interface', () => {
  // Create a test implementation
  class TestNodeExecutor implements NodeExecutor {
    readonly type = 'test' as const;

    async execute(
      config: NodeConfig,
      params: Record<string, unknown>,
      context: ExecutionContext
    ): Promise<NodeResult> {
      return {
        success: true,
        output: { params, config: config.config },
        metadata: { executedBy: 'test' },
      };
    }

    validate(config: NodeConfig): ValidationResult {
      if (!config.config.required_field) {
        return {
          valid: false,
          errors: ['Missing required_field'],
        };
      }
      return { valid: true, errors: [] };
    }
  }

  let executor: TestNodeExecutor;

  beforeEach(() => {
    executor = new TestNodeExecutor();
  });

  describe('execute', () => {
    it('should execute and return result', async () => {
      const config: NodeConfig = {
        nodeId: 'test_node_1',
        type: 'test',
        config: { required_field: 'value' },
      };
      const params = { input: 'data' };
      const context: ExecutionContext = {
        workflowId: 'wf_1',
        stepResults: {},
        variables: {},
        secrets: {},
      };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({
        params: { input: 'data' },
        config: { required_field: 'value' },
      });
    });
  });

  describe('validate', () => {
    it('should validate valid config', () => {
      const config: NodeConfig = {
        nodeId: 'test_node',
        type: 'test',
        config: { required_field: 'value' },
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect invalid config', () => {
      const config: NodeConfig = {
        nodeId: 'test_node',
        type: 'test',
        config: {},
      };

      const result = executor.validate(config);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Missing required_field');
    });
  });
});

describe('NodeRegistry', () => {
  let registry: NodeRegistry;

  // Test executor
  class MockExecutor implements NodeExecutor {
    readonly type = 'mock' as const;
    async execute(): Promise<NodeResult> {
      return { success: true, output: {} };
    }
    validate(): ValidationResult {
      return { valid: true, errors: [] };
    }
  }

  beforeEach(() => {
    registry = new NodeRegistry();
  });

  describe('register', () => {
    it('should register a node executor', () => {
      registry.register('mock', new MockExecutor());

      expect(registry.has('mock')).toBe(true);
    });
  });

  describe('get', () => {
    it('should return registered executor', () => {
      const executor = new MockExecutor();
      registry.register('mock', executor);

      expect(registry.get('mock')).toBe(executor);
    });

    it('should return undefined for unknown type', () => {
      expect(registry.get('unknown')).toBeUndefined();
    });
  });

  describe('has', () => {
    it('should return true for registered type', () => {
      registry.register('mock', new MockExecutor());
      expect(registry.has('mock')).toBe(true);
    });

    it('should return false for unregistered type', () => {
      expect(registry.has('unknown')).toBe(false);
    });
  });

  describe('listTypes', () => {
    it('should list all registered types', () => {
      registry.register('mock', new MockExecutor());
      registry.register('mock2', new MockExecutor());

      const types = registry.listTypes();

      expect(types).toContain('mock');
      expect(types).toContain('mock2');
    });
  });
});

describe('createNodeRegistry factory', () => {
  it('should create an empty registry', () => {
    const registry = createNodeRegistry();
    expect(registry.listTypes()).toHaveLength(0);
  });
});
