/**
 * TransformNode Unit Tests
 *
 * Issue #363: Data transformation node executor
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  TransformNodeExecutor,
  createTransformNodeExecutor,
} from '../../../../src/taskflowEngine/nodes/TransformNode.js';
import type { NodeConfig, ExecutionContext } from '../../../../src/taskflowEngine/nodes/BaseNode.js';

describe('TransformNodeExecutor', () => {
  let executor: TransformNodeExecutor;
  let context: ExecutionContext;

  beforeEach(() => {
    executor = new TransformNodeExecutor();
    context = {
      workflowId: 'wf_test',
      stepResults: {},
      variables: {},
      secrets: {},
    };
  });

  describe('type', () => {
    it('should have type transform', () => {
      expect(executor.type).toBe('transform');
    });
  });

  describe('validate', () => {
    it('should validate config with template', () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: '{"name": "{{name}}"}',
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should validate config with mapping', () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          mapping: {
            output_name: '$.input.name',
          },
        },
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(true);
    });

    it('should require template or mapping', () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {},
      };

      const result = executor.validate(config);
      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Either template or mapping is required');
    });
  });

  describe('execute', () => {
    it('should transform using template', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: '{"fullName": "{{firstName}} {{lastName}}"}',
        },
      };
      const params = { firstName: 'John', lastName: 'Doe' };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ fullName: 'John Doe' });
    });

    it('should transform using mapping', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          mapping: {
            userName: 'name',
            userAge: 'age',
          },
        },
      };
      const params = { name: 'Alice', age: 30, extra: 'ignored' };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ userName: 'Alice', userAge: 30 });
    });

    it('should handle nested template values', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: '{"address": "{{user.address.city}}"}',
        },
      };
      const params = {
        user: {
          address: {
            city: 'Tokyo',
          },
        },
      };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ address: 'Tokyo' });
    });

    it('should handle missing template values', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: '{"name": "{{name}}", "missing": "{{notFound}}"}',
        },
      };
      const params = { name: 'Test' };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      // Missing values should be empty string
      expect(result.output).toEqual({ name: 'Test', missing: '' });
    });

    it('should handle array transformations', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: '{"items": {{items}}}',
        },
      };
      const params = { items: [1, 2, 3] };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toEqual({ items: [1, 2, 3] });
    });

    it('should return string output for non-JSON template', async () => {
      // Template that can't be parsed as JSON returns as string
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          template: 'Hello, {{name}}!',
        },
      };
      const params = { name: 'World' };

      const result = await executor.execute(config, params, context);

      expect(result.success).toBe(true);
      expect(result.output).toBe('Hello, World!');
    });

    it('should handle missing configuration', async () => {
      const config: NodeConfig = {
        nodeId: 'transform_1',
        type: 'transform',
        config: {
          // No template or mapping
        },
      };

      const result = await executor.execute(config, {}, context);

      expect(result.success).toBe(false);
      expect(result.error?.code).toBe('TRANSFORM_ERROR');
    });
  });
});

describe('createTransformNodeExecutor factory', () => {
  it('should create a TransformNodeExecutor instance', () => {
    const executor = createTransformNodeExecutor();
    expect(executor).toBeInstanceOf(TransformNodeExecutor);
  });
});
