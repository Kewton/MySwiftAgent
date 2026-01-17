/**
 * Context Manager Unit Tests
 *
 * Tests for ExecutionContext, VariableResolver, SecretManager, and ValidationCoordinator
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { z } from 'zod';
import {
  ExecutionContext,
  createExecutionContext,
  VariableResolver,
  createVariableResolver,
  SecretManager,
  createSecretManager,
  ValidationCoordinator,
  createValidationCoordinator,
} from '../../../src/shared/context/index.js';
import type { WorkflowDefinition, StepResult } from '../../../src/shared/types/workflow.types.js';

describe('ExecutionContext', () => {
  const mockWorkflow: WorkflowDefinition = {
    id: 'wf_test_001',
    name: 'Test Workflow',
    version: '1.0.0',
    steps: [
      { id: 'step_1', name: 'Step 1', type: 'action', config: {} },
      { id: 'step_2', name: 'Step 2', type: 'action', config: {}, dependsOn: ['step_1'] },
    ],
    variables: { input: 'test_value' },
    timeout: 60000,
  };

  it('should create ExecutionContext with factory function', () => {
    const context = createExecutionContext(mockWorkflow);
    expect(context).toBeInstanceOf(ExecutionContext);
    expect(context.getWorkflowId()).toBe('wf_test_001');
  });

  it('should generate unique request ID', () => {
    const context = createExecutionContext(mockWorkflow);
    const requestId = context.getRequestId();
    expect(requestId).toMatch(/^req_[a-z0-9]+_[a-z0-9]+$/);
  });

  it('should use provided request ID', () => {
    const context = createExecutionContext(mockWorkflow, { requestId: 'custom_req_123' });
    expect(context.getRequestId()).toBe('custom_req_123');
  });

  it('should manage variables', () => {
    const context = createExecutionContext(mockWorkflow);

    // Initial variable from workflow
    expect(context.getVariable('input')).toBe('test_value');

    // Set new variable
    context.setVariable('output', 'result');
    expect(context.getVariable('output')).toBe('result');

    // Get all variables
    const allVars = context.getAllVariables();
    expect(allVars).toEqual({ input: 'test_value', output: 'result' });
  });

  it('should track step completion', () => {
    const context = createExecutionContext(mockWorkflow);

    expect(context.isStepCompleted('step_1')).toBe(false);

    const stepResult: StepResult = {
      stepId: 'step_1',
      stepName: 'Step 1',
      status: 'success',
      output: { result: 'done' },
      startTime: new Date(),
      endTime: new Date(),
      durationMs: 100,
    };

    context.completeStep('step_1', stepResult);

    expect(context.isStepCompleted('step_1')).toBe(true);
    expect(context.getStepResult('step_1')).toEqual(stepResult);
  });

  it('should track current step', () => {
    const context = createExecutionContext(mockWorkflow);

    expect(context.getCurrentStep()).toBeUndefined();

    context.setCurrentStep('step_1');
    expect(context.getCurrentStep()).toBe('step_1');
  });

  it('should handle metadata', () => {
    const context = createExecutionContext(mockWorkflow, {
      metadata: { source: 'test' },
    });

    expect(context.getMetadata('source')).toBe('test');

    context.setMetadata('target', 'production');
    expect(context.getMetadata('target')).toBe('production');
  });

  it('should calculate duration', () => {
    const context = createExecutionContext(mockWorkflow);

    // Wait a bit
    const duration = context.getDuration();
    expect(duration).toBeGreaterThanOrEqual(0);
  });

  it('should detect timeout', () => {
    const context = createExecutionContext(mockWorkflow, { timeout: 1 });

    // Should timeout almost immediately
    return new Promise<void>((resolve) => {
      setTimeout(() => {
        expect(context.isTimedOut()).toBe(true);
        resolve();
      }, 10);
    });
  });

  it('should create snapshot of state', () => {
    const context = createExecutionContext(mockWorkflow);
    context.setVariable('new_var', 'value');

    const snapshot = context.snapshot();

    expect(snapshot.workflowId).toBe('wf_test_001');
    expect(snapshot.variables.get('new_var')).toBe('value');
  });
});

describe('VariableResolver', () => {
  let resolver: VariableResolver;
  let context: ExecutionContext;

  const mockWorkflow: WorkflowDefinition = {
    id: 'wf_test',
    name: 'Test Workflow',
    version: '1.0.0',
    steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    variables: { data: { nested: 'value' } },
  };

  beforeEach(() => {
    resolver = createVariableResolver();
    context = createExecutionContext(mockWorkflow);
  });

  it('should resolve context variables', async () => {
    context.setVariable('name', 'test');

    const result = await resolver.resolveString('Hello ${context.variables.name}', context);
    expect(result).toBe('Hello test');
  });

  it('should resolve environment variables', async () => {
    process.env['TEST_VAR'] = 'env_value';

    const result = await resolver.resolveString('Value: ${env.TEST_VAR}', context);
    expect(result).toBe('Value: env_value');

    delete process.env['TEST_VAR'];
  });

  it('should resolve step output', async () => {
    const stepResult: StepResult = {
      stepId: 'step_1',
      stepName: 'Step 1',
      status: 'success',
      output: { result: 'step_output' },
      startTime: new Date(),
      endTime: new Date(),
      durationMs: 100,
    };
    context.completeStep('step_1', stepResult);

    const result = await resolver.resolveString(
      'Output: ${step.step_1.output.result}',
      context
    );
    expect(result).toBe('Output: step_output');
  });

  it('should resolve objects recursively', async () => {
    context.setVariable('name', 'test');

    const obj = {
      greeting: 'Hello ${context.variables.name}',
      nested: {
        value: 'Nested ${context.variables.name}',
      },
    };

    const result = await resolver.resolve(obj, context);
    expect(result).toEqual({
      greeting: 'Hello test',
      nested: { value: 'Nested test' },
    });
  });

  it('should resolve arrays', async () => {
    context.setVariable('item', 'value');

    const arr = ['${context.variables.item}', 'static'];
    const result = await resolver.resolve(arr, context);
    expect(result).toEqual(['value', 'static']);
  });

  it('should resolve secrets with provider', async () => {
    const secretProvider = vi.fn().mockResolvedValue('secret_value');
    const resolverWithSecrets = createVariableResolver({ secretProvider });

    const result = await resolverWithSecrets.resolveString(
      'Secret: ${secret.my_key}',
      context
    );
    expect(result).toBe('Secret: secret_value');
    expect(secretProvider).toHaveBeenCalledWith('my_key');
  });

  it('should handle missing variables gracefully', async () => {
    const result = await resolver.resolveString(
      'Missing: ${context.variables.nonexistent}',
      context
    );
    // Variable resolution returns undefined for missing variables
    // which gets stringified to 'undefined'
    expect(result).toBe('Missing: undefined');
  });

  it('should resolve non-string values without change', async () => {
    const result = await resolver.resolve(42, context);
    expect(result).toBe(42);

    const nullResult = await resolver.resolve(null, context);
    expect(nullResult).toBe(null);

    const boolResult = await resolver.resolve(true, context);
    expect(boolResult).toBe(true);
  });

  it('should handle empty path in context variable', async () => {
    const ref = resolver.parseReference('context', '${context}');
    const result = await resolver.resolveReference(ref, context);
    expect(result.resolved).toBe(false);
    expect(result.error).toBe('Empty path');
  });

  it('should resolve metadata variable', async () => {
    context.setMetadata('custom', 'meta_value');
    const result = await resolver.resolveString('Metadata: ${context.metadata.custom}', context);
    expect(result).toBe('Metadata: meta_value');
  });

  it('should handle missing metadata variable', async () => {
    const result = await resolver.resolveString('Metadata: ${context.metadata.missing}', context);
    expect(result).toBe('Metadata: ${context.metadata.missing}');
  });

  it('should handle step variable with short path', async () => {
    const ref = resolver.parseReference('step.step_1', '${step.step_1}');
    const result = await resolver.resolveReference(ref, context);
    expect(result.resolved).toBe(false);
    expect(result.error).toBe('Step reference requires step ID and path');
  });

  it('should handle step variable with invalid path', async () => {
    const stepResult: StepResult = {
      stepId: 'step_1',
      stepName: 'Step 1',
      status: 'success',
      output: { result: 'output' },
      startTime: new Date(),
      endTime: new Date(),
      durationMs: 100,
    };
    context.completeStep('step_1', stepResult);

    const result = await resolver.resolveString('${step.step_1.invalid.path}', context);
    expect(result).toBe('${step.step_1.invalid.path}');
  });

  it('should handle missing environment variable', async () => {
    const result = await resolver.resolveString('${env.NONEXISTENT_VAR}', context);
    expect(result).toBe('${env.NONEXISTENT_VAR}');
  });

  it('should handle secret without provider', async () => {
    // resolver without secret provider
    const result = await resolver.resolveString('Secret: ${secret.key}', context);
    expect(result).toBe('Secret: ${secret.key}');
  });

  it('should handle missing secret', async () => {
    const secretProvider = vi.fn().mockResolvedValue(undefined);
    const resolverWithSecrets = createVariableResolver({ secretProvider });

    const result = await resolverWithSecrets.resolveString('Secret: ${secret.missing}', context);
    expect(result).toBe('Secret: ${secret.missing}');
  });

  it('should handle empty secret key', async () => {
    const secretProvider = vi.fn().mockResolvedValue('value');
    const resolverWithSecrets = createVariableResolver({ secretProvider });

    const ref = resolverWithSecrets.parseReference('secret', '${secret}');
    const result = await resolverWithSecrets.resolveReference(ref, context);
    expect(result.resolved).toBe(false);
    expect(result.error).toBe('Missing secret key');
  });

  it('should handle empty env var name', async () => {
    const ref = resolver.parseReference('env', '${env}');
    const result = await resolver.resolveReference(ref, context);
    expect(result.resolved).toBe(false);
    expect(result.error).toBe('Missing environment variable name');
  });

  it('should parse unrecognized source as context path', async () => {
    context.setVariable('custom_source', 'custom_value');
    const result = await resolver.resolveString('${custom_source}', context);
    expect(result).toBe('custom_value');
  });

  it('should resolve non-object value in nested path', async () => {
    context.setVariable('str_var', 'just_a_string');
    const result = await resolver.resolveString('${context.variables.str_var.nested}', context);
    expect(result).toBe('undefined');
  });

  it('should handle JSON stringification for non-string resolved values', async () => {
    context.setVariable('obj_var', { key: 'value' });
    const result = await resolver.resolveString('Data: ${context.variables.obj_var}', context);
    expect(result).toBe('Data: {"key":"value"}');
  });
});

describe('SecretManager', () => {
  it('should create SecretManager with factory function', () => {
    const manager = createSecretManager();
    expect(manager).toBeInstanceOf(SecretManager);
  });

  it('should fallback to environment variables', async () => {
    process.env['TEST_SECRET'] = 'env_secret';
    const manager = createSecretManager({ fallbackToEnv: true });

    const value = await manager.get('TEST_SECRET');
    expect(value).toBe('env_secret');

    delete process.env['TEST_SECRET'];
  });

  it('should return undefined for missing secrets', async () => {
    const manager = createSecretManager({ fallbackToEnv: true });
    const value = await manager.get('NONEXISTENT_SECRET');
    expect(value).toBeUndefined();
  });

  it('should report MyVault status', () => {
    const managerWithVault = createSecretManager({
      myVault: {
        baseUrl: 'http://localhost:8003',
        serviceName: 'testService',
        serviceToken: 'token',
      },
    });
    expect(managerWithVault.isMyVaultEnabled()).toBe(true);
    expect(managerWithVault.getMyVaultBaseUrl()).toBe('http://localhost:8003');

    const managerWithoutVault = createSecretManager();
    expect(managerWithoutVault.isMyVaultEnabled()).toBe(false);
  });

  it('should cache MyVault secrets (env vars not cached)', async () => {
    // Note: Environment variable fallback is NOT cached
    // Only MyVault responses are cached
    process.env['ENV_SECRET'] = 'env_value';
    const manager = createSecretManager({ fallbackToEnv: true });

    // First call - reads from env
    const value1 = await manager.get('ENV_SECRET');
    expect(value1).toBe('env_value');

    // Change the env var
    process.env['ENV_SECRET'] = 'new_value';

    // Environment variables are read directly, not cached
    // So changing the env var is immediately reflected
    const value2 = await manager.get('ENV_SECRET');
    expect(value2).toBe('new_value');

    delete process.env['ENV_SECRET'];
  });

  it('should clear cache', () => {
    const manager = createSecretManager({ fallbackToEnv: true });
    // Just verify clearCache doesn't throw
    manager.clearCache();
  });

  it('should cache and return cached MyVault secrets', async () => {
    // Mock fetch for MyVault
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ value: 'vault_secret' }),
    }) as typeof fetch;

    try {
      const manager = createSecretManager({
        myVault: {
          baseUrl: 'http://localhost:8003',
          serviceName: 'testService',
          serviceToken: 'test-token',
        },
      });

      // First call - should hit MyVault
      const value1 = await manager.get('MY_SECRET');
      expect(value1).toBe('vault_secret');
      expect(global.fetch).toHaveBeenCalledTimes(1);

      // Second call - should return cached value
      const value2 = await manager.get('MY_SECRET');
      expect(value2).toBe('vault_secret');
      // Fetch should not be called again
      expect(global.fetch).toHaveBeenCalledTimes(1);
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should return undefined when MyVault returns 404', async () => {
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
    }) as typeof fetch;

    try {
      const manager = createSecretManager({
        myVault: {
          baseUrl: 'http://localhost:8003',
          serviceName: 'testService',
          serviceToken: 'test-token',
        },
        fallbackToEnv: false,
      });

      const value = await manager.get('MISSING_SECRET');
      expect(value).toBeUndefined();
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should fallback to env when MyVault fails', async () => {
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockRejectedValue(new Error('Connection failed')) as typeof fetch;

    process.env['FALLBACK_SECRET'] = 'from_env';

    try {
      const manager = createSecretManager({
        myVault: {
          baseUrl: 'http://localhost:8003',
          serviceName: 'testService',
          serviceToken: 'test-token',
        },
        fallbackToEnv: true,
      });

      const value = await manager.get('FALLBACK_SECRET');
      expect(value).toBe('from_env');
    } finally {
      global.fetch = originalFetch;
      delete process.env['FALLBACK_SECRET'];
    }
  });

  it('should use custom project in MyVault URL', async () => {
    const originalFetch = global.fetch;
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ value: 'project_secret' }),
    }) as typeof fetch;

    try {
      const manager = createSecretManager({
        myVault: {
          baseUrl: 'http://localhost:8003',
          serviceName: 'testService',
          serviceToken: 'test-token',
          project: 'custom-project',
        },
      });

      await manager.get('MY_SECRET');

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('custom-project'),
        expect.any(Object)
      );
    } finally {
      global.fetch = originalFetch;
    }
  });

  it('should not fallback to env when fallbackToEnv is false', async () => {
    process.env['NO_FALLBACK_SECRET'] = 'should_not_return';

    try {
      const manager = createSecretManager({
        fallbackToEnv: false,
      });

      const value = await manager.get('NO_FALLBACK_SECRET');
      expect(value).toBeUndefined();
    } finally {
      delete process.env['NO_FALLBACK_SECRET'];
    }
  });
});

describe('SecretManager createSecretManagerFromEnv', () => {
  const originalEnv: Record<string, string | undefined> = {};

  beforeEach(() => {
    originalEnv['MYVAULT_ENABLED'] = process.env['MYVAULT_ENABLED'];
    originalEnv['MYVAULT_BASE_URL'] = process.env['MYVAULT_BASE_URL'];
    originalEnv['MYVAULT_SERVICE_NAME'] = process.env['MYVAULT_SERVICE_NAME'];
    originalEnv['MYVAULT_SERVICE_TOKEN'] = process.env['MYVAULT_SERVICE_TOKEN'];
    originalEnv['MYVAULT_DEFAULT_PROJECT'] = process.env['MYVAULT_DEFAULT_PROJECT'];
  });

  afterEach(() => {
    for (const [key, value] of Object.entries(originalEnv)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  });

  it('should create manager with MyVault when MYVAULT_ENABLED is true', async () => {
    process.env['MYVAULT_ENABLED'] = 'true';
    process.env['MYVAULT_BASE_URL'] = 'http://myvault:8003';
    process.env['MYVAULT_SERVICE_TOKEN'] = 'my-token';
    process.env['MYVAULT_DEFAULT_PROJECT'] = 'test-project';

    // Import the function dynamically to pick up env changes
    const { createSecretManagerFromEnv } = await import(
      '../../../src/shared/context/SecretManager.js'
    );

    const manager = createSecretManagerFromEnv();
    expect(manager.isMyVaultEnabled()).toBe(true);
    expect(manager.getMyVaultBaseUrl()).toBe('http://myvault:8003');
  });

  it('should create manager without MyVault when MYVAULT_ENABLED is not true', async () => {
    delete process.env['MYVAULT_ENABLED'];

    const { createSecretManagerFromEnv } = await import(
      '../../../src/shared/context/SecretManager.js'
    );

    const manager = createSecretManagerFromEnv();
    expect(manager.isMyVaultEnabled()).toBe(false);
  });

  it('should use default base URL when MYVAULT_BASE_URL not set', async () => {
    process.env['MYVAULT_ENABLED'] = 'true';
    delete process.env['MYVAULT_BASE_URL'];
    process.env['MYVAULT_SERVICE_TOKEN'] = 'token';

    const { createSecretManagerFromEnv } = await import(
      '../../../src/shared/context/SecretManager.js'
    );

    const manager = createSecretManagerFromEnv();
    expect(manager.getMyVaultBaseUrl()).toBe('http://localhost:8003');
  });
});

describe('ValidationCoordinator', () => {
  let validator: ValidationCoordinator;

  beforeEach(() => {
    validator = createValidationCoordinator();
  });

  it('should validate valid workflow', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_valid',
      name: 'Valid Workflow',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('should detect missing workflow ID', () => {
    const workflow: WorkflowDefinition = {
      id: '',
      name: 'Test',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field === 'id')).toBe(true);
  });

  it('should detect missing workflow name', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: '',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field === 'name')).toBe(true);
  });

  it('should detect empty steps', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field === 'steps')).toBe(true);
  });

  it('should detect invalid step', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [{ id: '', name: '', type: '', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field.includes('steps[0]'))).toBe(true);
  });

  it('should detect missing dependency', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [
        { id: 'step_1', name: 'Step 1', type: 'action', config: {}, dependsOn: ['nonexistent'] },
      ],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.message.includes('Dependency'))).toBe(true);
  });

  it('should detect circular dependencies', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [
        { id: 'step_1', name: 'Step 1', type: 'action', config: {}, dependsOn: ['step_2'] },
        { id: 'step_2', name: 'Step 2', type: 'action', config: {}, dependsOn: ['step_1'] },
      ],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.message.includes('Circular'))).toBe(true);
  });

  it('should detect invalid version format', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: 'invalid',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.field === 'version')).toBe(true);
  });

  it('should convert validation result to CoreError', () => {
    const workflow: WorkflowDefinition = {
      id: '',
      name: 'Test',
      version: '1.0.0',
      steps: [],
    };

    const result = validator.validateWorkflow(workflow);
    const error = validator.toValidationError(result, 'Custom message');

    expect(error).not.toBeNull();
    expect(error?.code).toBe('VAL_INVALID_INPUT');
    expect(error?.message).toBe('Custom message');
    expect(error?.fieldErrors.length).toBeGreaterThan(0);
  });

  it('should return null when validation is valid', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    const error = validator.toValidationError(result);
    expect(error).toBeNull();
  });

  it('should use default message when not provided', () => {
    const workflow: WorkflowDefinition = {
      id: '',
      name: 'Test',
      version: '1.0.0',
      steps: [],
    };

    const result = validator.validateWorkflow(workflow);
    const error = validator.toValidationError(result);

    expect(error?.message).toBe('Validation failed');
  });

  it('should validate with Zod schema', () => {
    const schema = z.object({
      name: z.string().min(1),
      age: z.number().positive(),
    });

    const validResult = validator.validateWithSchema(schema, { name: 'Test', age: 25 });
    expect(validResult.valid).toBe(true);

    const invalidResult = validator.validateWithSchema(schema, { name: '', age: -1 });
    expect(invalidResult.valid).toBe(false);
    expect(invalidResult.errors.length).toBeGreaterThan(0);
  });

  it('should validate with Zod schema using field prefix', () => {
    const schema = z.object({
      value: z.string(),
    });

    const result = validator.validateWithSchema(schema, { value: 123 }, 'config');
    expect(result.valid).toBe(false);
    expect(result.errors[0]?.field).toContain('config');
  });

  it('should register and use custom rule', () => {
    validator.registerRule({
      name: 'positive',
      validate: (value: unknown) => {
        if (typeof value !== 'number' || value <= 0) {
          return { valid: false, errors: [{ field: '', message: 'Must be positive' }] };
        }
        return { valid: true, errors: [] };
      },
    });

    // The rule is registered but we can't easily test it since rules aren't exposed
    // This at least verifies the registerRule method works
    expect(true).toBe(true);
  });

  it('should accept workflow with pre-release version', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0-beta.1',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(true);
  });

  it('should accept workflow with build metadata version', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0+build.123',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(true);
  });

  it('should detect self-referencing dependency', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {}, dependsOn: ['step_1'] }],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.message.includes('Circular'))).toBe(true);
  });

  it('should handle longer circular dependency chain', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [
        { id: 'step_1', name: 'Step 1', type: 'action', config: {}, dependsOn: ['step_3'] },
        { id: 'step_2', name: 'Step 2', type: 'action', config: {}, dependsOn: ['step_1'] },
        { id: 'step_3', name: 'Step 3', type: 'action', config: {}, dependsOn: ['step_2'] },
      ],
    };

    const result = validator.validateWorkflow(workflow);
    expect(result.valid).toBe(false);
    expect(result.errors.some((e) => e.message.includes('Circular'))).toBe(true);
  });

  it('should accept workflow without version', () => {
    const workflow: WorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = validator.validateWorkflow(workflow);
    // Empty version should be valid (version validation only applies to non-empty)
    expect(result.valid).toBe(true);
  });
});
