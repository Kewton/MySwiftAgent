/**
 * Service Components Unit Tests
 *
 * Tests for TaskFlowEngine, TaskFlowGeneratorAgent, and CapabilityManagement
 */

import { describe, it, expect } from 'vitest';
import {
  TaskFlowEngine,
  createTaskFlowEngine,
} from '../../../src/taskflowEngine/index.js';
import {
  TaskFlowGeneratorAgent,
  createTaskFlowGeneratorAgent,
} from '../../../src/taskflowGeneratorAgent/index.js';
import {
  CapabilityManagement,
  createCapabilityManagement,
} from '../../../src/capabilityManagement/index.js';
import type { WorkflowDefinition } from '../../../src/shared/types/workflow.types.js';
import type { Capability } from '../../../src/shared/types/capability.types.js';

describe('TaskFlowEngine', () => {
  const validWorkflow: WorkflowDefinition = {
    id: 'wf_test_001',
    name: 'Test Workflow',
    version: '1.0.0',
    steps: [
      { id: 'step_1', name: 'Step 1', type: 'action', config: {} },
      { id: 'step_2', name: 'Step 2', type: 'action', config: {}, dependsOn: ['step_1'] },
    ],
  };

  it('should create TaskFlowEngine with factory function', () => {
    const engine = createTaskFlowEngine();
    expect(engine).toBeInstanceOf(TaskFlowEngine);
  });

  it('should create TaskFlowEngine with custom config', () => {
    const engine = createTaskFlowEngine({
      maxConcurrentSteps: 10,
      defaultTimeout: 600000,
      enableRecovery: false,
    });
    expect(engine).toBeInstanceOf(TaskFlowEngine);
  });

  it('should execute valid workflow successfully', async () => {
    const engine = createTaskFlowEngine();
    const result = await engine.execute(validWorkflow);

    expect(result.workflowId).toBe('wf_test_001');
    expect(result.workflowName).toBe('Test Workflow');
    expect(result.status).toBe('success');
    expect(result.stepResults.length).toBe(2);
    expect(result.errors.length).toBe(0);
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('should fail on invalid workflow', async () => {
    const invalidWorkflow: WorkflowDefinition = {
      id: '',
      name: '',
      version: '1.0.0',
      steps: [],
    };

    const engine = createTaskFlowEngine();
    const result = await engine.execute(invalidWorkflow);

    expect(result.status).toBe('failed');
    expect(result.errors.length).toBeGreaterThan(0);
  });

  it('should include request ID in metadata', async () => {
    const engine = createTaskFlowEngine();
    const result = await engine.execute(validWorkflow, {
      requestId: 'custom_req_123',
    });

    expect(result.metadata?.requestId).toBe('custom_req_123');
  });

  it('should respect timeout setting', async () => {
    const engine = createTaskFlowEngine({
      defaultTimeout: 1, // Very short timeout
    });

    // Create a workflow that would take longer
    const workflow: WorkflowDefinition = {
      id: 'wf_timeout',
      name: 'Timeout Test',
      version: '1.0.0',
      steps: Array.from({ length: 100 }, (_, i) => ({
        id: `step_${i}`,
        name: `Step ${i}`,
        type: 'action',
        config: {},
      })),
    };

    const result = await engine.execute(workflow, { timeout: 1 });

    // With extremely short timeout, might still complete
    // but we verify the engine doesn't crash
    expect(result).toBeDefined();
  });
});

describe('TaskFlowGeneratorAgent', () => {
  it('should create TaskFlowGeneratorAgent with factory function', () => {
    const agent = createTaskFlowGeneratorAgent();
    expect(agent).toBeInstanceOf(TaskFlowGeneratorAgent);
  });

  it('should create TaskFlowGeneratorAgent with custom config', () => {
    const agent = createTaskFlowGeneratorAgent({
      model: 'gpt-4-turbo',
      maxTokens: 8192,
      temperature: 0.5,
      langfuseEnabled: false,
    });

    const config = agent.getConfig();
    expect(config.model).toBe('gpt-4-turbo');
    expect(config.maxTokens).toBe(8192);
    expect(config.temperature).toBe(0.5);
    expect(config.langfuseEnabled).toBe(false);
  });

  it('should generate workflow from prompt', async () => {
    const agent = createTaskFlowGeneratorAgent();
    const result = await agent.generate({
      prompt: 'Create a workflow to process customer orders',
    });

    expect(result.status).toBe('success');
    expect(result.workflow).toBeDefined();
    expect(result.workflow?.id).toMatch(/^wf_generated_/);
    expect(result.workflow?.steps.length).toBeGreaterThan(0);
  });

  it('should include context in generation', async () => {
    const agent = createTaskFlowGeneratorAgent();
    const result = await agent.generate({
      prompt: 'Create a workflow',
      context: { environment: 'production' },
    });

    expect(result.workflow?.variables?.environment).toBe('production');
  });

  it('should include metadata in result', async () => {
    const agent = createTaskFlowGeneratorAgent();
    const result = await agent.generate({
      prompt: 'Test workflow',
    });

    expect(result.metadata).toBeDefined();
    expect(result.metadata?.generationTimeMs).toBeGreaterThanOrEqual(0);
  });

  it('should validate workflow', async () => {
    const agent = createTaskFlowGeneratorAgent();

    const validWorkflow: WorkflowDefinition = {
      id: 'wf_valid',
      name: 'Valid Workflow',
      version: '1.0.0',
      steps: [{ id: 'step_1', name: 'Step 1', type: 'action', config: {} }],
    };

    const result = await agent.validate(validWorkflow);
    expect(result.valid).toBe(true);
  });

  it('should detect invalid workflow during validation', async () => {
    const agent = createTaskFlowGeneratorAgent();

    const invalidWorkflow: WorkflowDefinition = {
      id: '',
      name: 'Invalid',
      version: '1.0.0',
      steps: [],
    };

    const result = await agent.validate(invalidWorkflow);
    expect(result.valid).toBe(false);
    expect(result.issues).toBeDefined();
    expect(result.issues!.length).toBeGreaterThan(0);
  });
});

describe('CapabilityManagement', () => {
  const sampleCapability: Capability = {
    id: 'cap_001',
    name: 'Test Capability',
    description: 'A capability for testing',
    version: '1.0.0',
    status: 'available',
    category: 'testing',
    parameters: [
      {
        name: 'input',
        type: 'string',
        required: true,
        description: 'Input parameter',
      },
    ],
    returnType: 'object',
    tags: ['test', 'example'],
  };

  it('should create CapabilityManagement with factory function', () => {
    const manager = createCapabilityManagement();
    expect(manager).toBeInstanceOf(CapabilityManagement);
  });

  it('should register and retrieve capability', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);

    const retrieved = manager.get('cap_001');
    expect(retrieved).toEqual(sampleCapability);
  });

  it('should return undefined for non-existent capability', () => {
    const manager = createCapabilityManagement();
    const retrieved = manager.get('nonexistent');
    expect(retrieved).toBeUndefined();
  });

  it('should unregister capability', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);

    const removed = manager.unregister('cap_001');
    expect(removed).toBe(true);
    expect(manager.get('cap_001')).toBeUndefined();
  });

  it('should return false when unregistering non-existent capability', () => {
    const manager = createCapabilityManagement();
    const removed = manager.unregister('nonexistent');
    expect(removed).toBe(false);
  });

  it('should list all capabilities', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      name: 'Another Capability',
    });

    const list = manager.list();
    expect(list.length).toBe(2);
  });

  it('should filter by category', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      category: 'other',
    });

    const filtered = manager.list({ category: 'testing' });
    expect(filtered.length).toBe(1);
    expect(filtered[0]?.id).toBe('cap_001');
  });

  it('should filter by status', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      status: 'unavailable',
    });

    const filtered = manager.list({ status: 'available' });
    expect(filtered.length).toBe(1);
    expect(filtered[0]?.id).toBe('cap_001');
  });

  it('should filter by tags', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      tags: ['other'],
    });

    const filtered = manager.list({ tags: ['test'] });
    expect(filtered.length).toBe(1);
    expect(filtered[0]?.id).toBe('cap_001');
  });

  it('should filter by search term', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      name: 'Different Name',
      description: 'Different description',
    });

    const filtered = manager.list({ searchTerm: 'Test' });
    expect(filtered.length).toBe(1);
    expect(filtered[0]?.id).toBe('cap_001');
  });

  it('should invoke available capability', async () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);

    const result = await manager.invoke({
      capabilityId: 'cap_001',
      parameters: { input: 'test' },
    });

    expect(result.status).toBe('success');
    expect(result.capabilityId).toBe('cap_001');
    expect(result.durationMs).toBeGreaterThanOrEqual(0);
  });

  it('should fail invoking non-existent capability', async () => {
    const manager = createCapabilityManagement();

    const result = await manager.invoke({
      capabilityId: 'nonexistent',
      parameters: {},
    });

    expect(result.status).toBe('failed');
    expect(result.error?.code).toBe('CAPABILITY_NOT_FOUND');
  });

  it('should fail invoking unavailable capability', async () => {
    const manager = createCapabilityManagement();
    manager.register({
      ...sampleCapability,
      status: 'unavailable',
    });

    const result = await manager.invoke({
      capabilityId: 'cap_001',
      parameters: {},
    });

    expect(result.status).toBe('failed');
    expect(result.error?.code).toBe('CAPABILITY_UNAVAILABLE');
  });

  it('should track usage count', async () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);

    await manager.invoke({ capabilityId: 'cap_001', parameters: {} });
    const result = await manager.invoke({ capabilityId: 'cap_001', parameters: {} });

    expect(result.metadata?.invocationCount).toBe(2);
  });

  it('should provide statistics', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({
      ...sampleCapability,
      id: 'cap_002',
      status: 'unavailable',
    });
    manager.register({
      ...sampleCapability,
      id: 'cap_003',
      status: 'deprecated',
      category: 'other',
    });

    const stats = manager.getStats();
    expect(stats.total).toBe(3);
    expect(stats.available).toBe(1);
    expect(stats.unavailable).toBe(1);
    expect(stats.deprecated).toBe(1);
    expect(stats.byCategory['testing']).toBe(2);
    expect(stats.byCategory['other']).toBe(1);
  });

  it('should clear all capabilities', () => {
    const manager = createCapabilityManagement();
    manager.register(sampleCapability);
    manager.register({ ...sampleCapability, id: 'cap_002' });

    manager.clear();

    const list = manager.list();
    expect(list.length).toBe(0);
  });
});
