/**
 * PromptBuilder Unit Tests
 *
 * Issue #364: Prompt construction for workflow generation
 */

import { describe, it, expect } from 'vitest';
import {
  PromptBuilder,
  createPromptBuilder,
} from '../../../../src/taskflowGeneratorAgent/prompts/PromptBuilder.js';
import type {
  TaskGenerationRequest,
  Capability,
} from '../../../../src/taskflowGeneratorAgent/types/generator.js';

describe('PromptBuilder', () => {
  let builder: PromptBuilder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  describe('buildSystemPrompt', () => {
    it('should include TaskFlow rules', () => {
      const capabilities: Capability[] = [];

      const prompt = builder.buildSystemPrompt(capabilities);

      expect(prompt).toContain('TaskFlow');
      expect(prompt).toContain('workflow_name');
      expect(prompt).toContain('steps');
    });

    it('should include capabilities section', () => {
      const capabilities: Capability[] = [
        {
          id: 'user_api',
          name: 'User API',
          description: 'Get user information',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'user_id', type: 'string', required: true },
          ],
        },
      ];

      const prompt = builder.buildSystemPrompt(capabilities);

      expect(prompt).toContain('Available Capabilities');
      expect(prompt).toContain('User API');
      expect(prompt).toContain('user_api');
      expect(prompt).toContain('user_id');
    });

    it('should only include available capabilities', () => {
      const capabilities: Capability[] = [
        {
          id: 'available_api',
          name: 'Available API',
          category: 'api',
          status: 'available',
        },
        {
          id: 'unavailable_api',
          name: 'Unavailable API',
          category: 'api',
          status: 'unavailable',
        },
        {
          id: 'deprecated_api',
          name: 'Deprecated API',
          category: 'api',
          status: 'deprecated',
        },
      ];

      const prompt = builder.buildSystemPrompt(capabilities);

      expect(prompt).toContain('Available API');
      expect(prompt).not.toContain('Unavailable API');
      expect(prompt).not.toContain('Deprecated API');
    });

    it('should group capabilities by category', () => {
      const capabilities: Capability[] = [
        { id: 'api_1', name: 'API 1', category: 'api', status: 'available' },
        { id: 'api_2', name: 'API 2', category: 'api', status: 'available' },
        { id: 'llm_1', name: 'LLM 1', category: 'llm', status: 'available' },
        { id: 'transform_1', name: 'Transform 1', category: 'transform', status: 'available' },
      ];

      const prompt = builder.buildSystemPrompt(capabilities);

      // Check that categories are present
      expect(prompt).toContain('api');
      expect(prompt).toContain('llm');
      expect(prompt).toContain('transform');
    });
  });

  describe('buildUserPrompt', () => {
    it('should include task information', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'User Analysis Report',
        description: 'Generate a user analysis report',
        interface: {
          input: { user_id: 'string' },
          output: { report: 'string' },
        },
      };

      const prompt = builder.buildUserPrompt(task);

      expect(prompt).toContain('task_001');
      expect(prompt).toContain('User Analysis Report');
      expect(prompt).toContain('Generate a user analysis report');
    });

    it('should include interface definition', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Test Task',
        description: 'Test description',
        interface: {
          input: { user_id: 'string', count: 'number' },
          output: { result: 'string', items: 'array' },
        },
      };

      const prompt = builder.buildUserPrompt(task);

      expect(prompt).toContain('user_id');
      expect(prompt).toContain('count');
      expect(prompt).toContain('result');
      expect(prompt).toContain('items');
    });

    it('should include dependencies', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_003',
        name: 'Final Task',
        description: 'Depends on other tasks',
        dependencies: ['task_001', 'task_002'],
        interface: {
          input: {},
          output: {},
        },
      };

      const prompt = builder.buildUserPrompt(task);

      expect(prompt).toContain('task_001');
      expect(prompt).toContain('task_002');
    });

    it('should include task_master_id if provided', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        task_master_id: 'tm_001',
        name: 'Test Task',
        description: 'Test description',
        interface: { input: {}, output: {} },
      };

      const prompt = builder.buildUserPrompt(task);

      expect(prompt).toContain('tm_001');
    });
  });

  describe('buildPrompt', () => {
    it('should build complete prompt with system and user', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Test Task',
        description: 'Test description',
        interface: { input: {}, output: {} },
      };

      const capabilities: Capability[] = [
        { id: 'api_1', name: 'API 1', category: 'api', status: 'available' },
      ];

      const prompt = builder.buildPrompt(task, capabilities);

      expect(prompt.system).toContain('TaskFlow');
      expect(prompt.system).toContain('API 1');
      expect(prompt.user).toContain('task_001');
      expect(prompt.user).toContain('Test Task');
    });
  });

  describe('formatCapabilities', () => {
    it('should format capabilities with parameters', () => {
      const capabilities: Capability[] = [
        {
          id: 'weather_api',
          name: 'Weather API',
          description: 'Get weather information',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'city', type: 'string', required: true, description: 'City name' },
            { name: 'units', type: 'string', required: false, description: 'Temperature units' },
          ],
        },
      ];

      const formatted = builder.formatCapabilities(capabilities);

      expect(formatted).toContain('Weather API');
      expect(formatted).toContain('weather_api');
      expect(formatted).toContain('city');
      expect(formatted).toContain('units');
      expect(formatted).toContain('required');
    });

    it('should handle capabilities without parameters', () => {
      const capabilities: Capability[] = [
        {
          id: 'simple_api',
          name: 'Simple API',
          category: 'api',
          status: 'available',
        },
      ];

      const formatted = builder.formatCapabilities(capabilities);

      expect(formatted).toContain('Simple API');
      expect(formatted).toContain('simple_api');
    });
  });
});

describe('createPromptBuilder', () => {
  it('should create PromptBuilder instance', () => {
    const builder = createPromptBuilder();

    expect(builder).toBeInstanceOf(PromptBuilder);
  });
});
