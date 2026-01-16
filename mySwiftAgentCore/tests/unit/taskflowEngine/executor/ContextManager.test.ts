/**
 * ContextManager Unit Tests
 *
 * Issue #363: Execution context management
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ContextManager,
  createContextManager,
} from '../../../../src/taskflowEngine/executor/ContextManager.js';
import type { InternalWorkflowDefinition } from '../../../../src/taskflowEngine/types/InternalWorkflowDefinition.js';

describe('ContextManager', () => {
  let manager: ContextManager;
  let workflow: InternalWorkflowDefinition;

  beforeEach(() => {
    workflow = {
      id: 'wf_test',
      name: 'Test Workflow',
      version: '1.0.0',
      steps: [],
      outputMapping: {},
      variables: { initialVar: 'value' },
    };
    manager = new ContextManager(workflow);
  });

  describe('constructor', () => {
    it('should create context with workflow ID', () => {
      expect(manager.getWorkflowId()).toBe('wf_test');
    });

    it('should initialize with workflow variables', () => {
      expect(manager.getVariable('initialVar')).toBe('value');
    });

    it('should accept initial secrets via config', () => {
      const managerWithSecrets = new ContextManager(workflow, {
        secrets: { API_KEY: 'secret123' },
      });
      const context = managerWithSecrets.getContext();
      expect(context.secrets['API_KEY']).toBe('secret123');
    });

    it('should accept initial variables via config', () => {
      const managerWithVars = new ContextManager(workflow, {
        variables: { configVar: 'configValue' },
      });
      expect(managerWithVars.getVariable('configVar')).toBe('configValue');
    });
  });

  describe('getContext', () => {
    it('should return execution context object', () => {
      const context = manager.getContext();

      expect(context.workflowId).toBe('wf_test');
      expect(context.stepResults).toEqual({});
      expect(context.variables).toEqual({ initialVar: 'value' });
      expect(context.secrets).toEqual({});
    });
  });

  describe('setStepResult', () => {
    it('should store step results', () => {
      manager.setStepResult('step_1', { data: 'result' });

      expect(manager.getStepResult('step_1')).toEqual({ data: 'result' });
    });

    it('should overwrite existing step result', () => {
      manager.setStepResult('step_1', 'first');
      manager.setStepResult('step_1', 'second');

      expect(manager.getStepResult('step_1')).toBe('second');
    });
  });

  describe('getStepResult', () => {
    it('should retrieve stored step result', () => {
      manager.setStepResult('step_1', 42);

      const result = manager.getStepResult('step_1');

      expect(result).toBe(42);
    });

    it('should return undefined for unknown step', () => {
      const result = manager.getStepResult('unknown');

      expect(result).toBeUndefined();
    });
  });

  describe('hasStepResult', () => {
    it('should return true when step has result', () => {
      manager.setStepResult('step_1', 'result');

      expect(manager.hasStepResult('step_1')).toBe(true);
    });

    it('should return false when step has no result', () => {
      expect(manager.hasStepResult('step_1')).toBe(false);
    });
  });

  describe('setVariable', () => {
    it('should set variable value', () => {
      manager.setVariable('counter', 10);

      expect(manager.getVariable('counter')).toBe(10);
    });

    it('should overwrite existing variable', () => {
      manager.setVariable('counter', 5);

      expect(manager.getVariable('counter')).toBe(5);
    });
  });

  describe('getVariable', () => {
    it('should return undefined for missing variable', () => {
      const value = manager.getVariable('missing');

      expect(value).toBeUndefined();
    });
  });

  describe('resolveValue', () => {
    it('should return non-string values unchanged', () => {
      const value = manager.resolveValue(42, {});

      expect(value).toBe(42);
    });

    it('should return string without ${} unchanged', () => {
      const value = manager.resolveValue('plain text', {});

      expect(value).toBe('plain text');
    });

    it('should resolve ${input.field} pattern', () => {
      const value = manager.resolveValue('${input.name}', { name: 'Alice' });

      expect(value).toBe('Alice');
    });

    it('should resolve step output reference', () => {
      manager.setStepResult('step_1', { output: { data: 'result' } });

      const value = manager.resolveValue('${step_1.output.data}', {});

      expect(value).toBe('result');
    });

    it('should return undefined for missing reference', () => {
      const value = manager.resolveValue('${missing.path}', {});

      expect(value).toBeUndefined();
    });
  });

  describe('buildOutput', () => {
    it('should build output from mapping', () => {
      manager.setStepResult('step_1', { result: 'data' });

      const output = manager.buildOutput(
        { finalResult: '${step_1.result}' },
        {}
      );

      expect(output.finalResult).toBe('data');
    });

    it('should handle multiple output fields', () => {
      manager.setStepResult('step_1', 'first');
      manager.setStepResult('step_2', 'second');

      const output = manager.buildOutput(
        {
          result1: '${step_1}',
          result2: '${step_2}',
        },
        {}
      );

      expect(output.result1).toBe('first');
      expect(output.result2).toBe('second');
    });
  });

  describe('getAllStepResults', () => {
    it('should return all step results', () => {
      manager.setStepResult('step_1', 'result1');
      manager.setStepResult('step_2', 'result2');

      const allResults = manager.getAllStepResults();

      expect(allResults).toEqual({
        step_1: 'result1',
        step_2: 'result2',
      });
    });

    it('should return empty object when no results', () => {
      const allResults = manager.getAllStepResults();

      expect(allResults).toEqual({});
    });
  });
});

describe('createContextManager factory', () => {
  it('should create a ContextManager instance', () => {
    const workflow: InternalWorkflowDefinition = {
      id: 'wf_test',
      name: 'Test',
      version: '1.0.0',
      steps: [],
      outputMapping: {},
    };
    const manager = createContextManager(workflow);
    expect(manager).toBeInstanceOf(ContextManager);
  });
});
