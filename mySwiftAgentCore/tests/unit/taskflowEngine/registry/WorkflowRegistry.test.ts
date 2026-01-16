/**
 * WorkflowRegistry Unit Tests
 *
 * Issue #363: Project-based workflow management
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  WorkflowRegistry,
  createWorkflowRegistry,
} from '../../../../src/taskflowEngine/registry/WorkflowRegistry.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('WorkflowRegistry', () => {
  let registry: WorkflowRegistry;

  const sampleWorkflow: InternalWorkflowDefinition = {
    id: 'wf_sample_123',
    name: 'sample_workflow',
    version: '1.0.0',
    steps: [
      {
        id: 'step_1',
        name: 'Step One',
        type: 'api_rest',
        config: { method: 'GET', url: 'https://api.example.com' },
        params: {},
      },
    ],
    inputSchema: { type: 'object', properties: {} },
    outputSchema: { type: 'object', properties: {} },
    outputMapping: {},
  };

  const anotherWorkflow: InternalWorkflowDefinition = {
    id: 'wf_another_456',
    name: 'another_workflow',
    version: '1.0.0',
    steps: [],
    inputSchema: { type: 'object', properties: {} },
    outputSchema: { type: 'object', properties: {} },
    outputMapping: {},
  };

  beforeEach(() => {
    registry = new WorkflowRegistry();
  });

  describe('registerForProject', () => {
    it('should register a workflow for a project', () => {
      registry.registerForProject('default_project', sampleWorkflow);

      const workflows = registry.getByProject('default_project');
      expect(workflows).toHaveLength(1);
      expect(workflows[0]?.name).toBe('sample_workflow');
    });

    it('should register multiple workflows for a project', () => {
      registry.registerForProject('default_project', sampleWorkflow);
      registry.registerForProject('default_project', anotherWorkflow);

      const workflows = registry.getByProject('default_project');
      expect(workflows).toHaveLength(2);
    });

    it('should update workflow if same id is registered', () => {
      registry.registerForProject('default_project', sampleWorkflow);

      const updatedWorkflow = { ...sampleWorkflow, version: '2.0.0' };
      registry.registerForProject('default_project', updatedWorkflow);

      const workflows = registry.getByProject('default_project');
      expect(workflows).toHaveLength(1);
      expect(workflows[0]?.version).toBe('2.0.0');
    });
  });

  describe('getByProject', () => {
    beforeEach(() => {
      registry.registerForProject('project_a', sampleWorkflow);
      registry.registerForProject('project_b', anotherWorkflow);
    });

    it('should return workflows for a specific project', () => {
      const workflows = registry.getByProject('project_a');
      expect(workflows).toHaveLength(1);
      expect(workflows[0]?.name).toBe('sample_workflow');
    });

    it('should return empty array for non-existent project', () => {
      const workflows = registry.getByProject('non_existent');
      expect(workflows).toEqual([]);
    });
  });

  describe('getWorkflow', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleWorkflow);
    });

    it('should return a specific workflow by project and name', () => {
      const workflow = registry.getWorkflow('default_project', 'sample_workflow');
      expect(workflow).toBeDefined();
      expect(workflow?.name).toBe('sample_workflow');
    });

    it('should return undefined for non-existent workflow', () => {
      const workflow = registry.getWorkflow('default_project', 'non_existent');
      expect(workflow).toBeUndefined();
    });

    it('should return undefined for non-existent project', () => {
      const workflow = registry.getWorkflow('non_existent', 'sample_workflow');
      expect(workflow).toBeUndefined();
    });
  });

  describe('getWorkflowById', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleWorkflow);
    });

    it('should return workflow by id', () => {
      const workflow = registry.getWorkflowById('default_project', 'wf_sample_123');
      expect(workflow).toBeDefined();
      expect(workflow?.id).toBe('wf_sample_123');
    });

    it('should return undefined for non-existent id', () => {
      const workflow = registry.getWorkflowById('default_project', 'wf_non_existent');
      expect(workflow).toBeUndefined();
    });
  });

  describe('unregisterFromProject', () => {
    beforeEach(() => {
      registry.registerForProject('default_project', sampleWorkflow);
    });

    it('should unregister a workflow from a project', () => {
      const result = registry.unregisterFromProject('default_project', 'sample_workflow');
      expect(result).toBe(true);

      const workflows = registry.getByProject('default_project');
      expect(workflows).toHaveLength(0);
    });

    it('should return false for non-existent workflow', () => {
      const result = registry.unregisterFromProject('default_project', 'non_existent');
      expect(result).toBe(false);
    });
  });

  describe('listProjects', () => {
    it('should return all project ids', () => {
      registry.registerForProject('project_1', sampleWorkflow);
      registry.registerForProject('project_2', anotherWorkflow);

      const projects = registry.listProjects();
      expect(projects).toContain('project_1');
      expect(projects).toContain('project_2');
    });
  });

  describe('getStats', () => {
    beforeEach(() => {
      registry.registerForProject('project_a', sampleWorkflow);
      registry.registerForProject('project_b', anotherWorkflow);
    });

    it('should return registry statistics', () => {
      const stats = registry.getStats();
      expect(stats.totalProjects).toBe(2);
      expect(stats.totalWorkflows).toBe(2);
    });
  });

  describe('clear', () => {
    it('should clear all projects and workflows', () => {
      registry.registerForProject('project_a', sampleWorkflow);
      registry.clear();

      const projects = registry.listProjects();
      expect(projects).toHaveLength(0);
    });
  });
});

describe('createWorkflowRegistry factory', () => {
  it('should create a WorkflowRegistry instance', () => {
    const registry = createWorkflowRegistry();
    expect(registry).toBeInstanceOf(WorkflowRegistry);
  });
});
