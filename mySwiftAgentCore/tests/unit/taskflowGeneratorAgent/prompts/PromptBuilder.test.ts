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

/**
 * Issue #373: capability_id rules tests
 */
describe('PromptBuilder - capability_id rules (Issue #373)', () => {
  let builder: PromptBuilder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  it('should include capability_id usage rules in system prompt', () => {
    const capabilities: Capability[] = [
      { id: 'google_search', name: 'Google Search', category: 'api', status: 'available' },
    ];

    const prompt = builder.buildSystemPrompt(capabilities);

    expect(prompt).toContain('capability_id');
    expect(prompt).toContain('google_search');
  });

  it('should explain when to use capability_id vs url', () => {
    const capabilities: Capability[] = [];

    const prompt = builder.buildSystemPrompt(capabilities);

    expect(prompt).toContain('capability_id');
    expect(prompt).toContain('url');
    expect(prompt).toContain('Internal Capability');
    expect(prompt).toContain('External API');
  });

  it('should include example of capability_id usage', () => {
    const capabilities: Capability[] = [];

    const prompt = builder.buildSystemPrompt(capabilities);

    expect(prompt).toContain('"capability_id"');
    expect(prompt).toContain('api_rest');
  });

  it('should include rule about not using both capability_id and url', () => {
    const capabilities: Capability[] = [];

    const prompt = builder.buildSystemPrompt(capabilities);

    expect(prompt).toContain('Never use both');
  });
});

/**
 * Issue #374: Enhanced Capability formatting tests
 */
describe('PromptBuilder - Enhanced Capability Formatting (Issue #374)', () => {
  let builder: PromptBuilder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  describe('formatCapabilitiesEnhanced', () => {
    it('should format capabilities with validation constraints', () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          description: 'Web search capability',
          category: 'api',
          status: 'available',
          parameters: [
            {
              name: 'queries',
              type: 'array',
              required: true,
              description: 'Search queries',
            },
            {
              name: 'num',
              type: 'number',
              required: false,
              description: 'Number of results',
              defaultValue: 10,
              validation: { min: 1, max: 100 },
            },
          ],
        },
      ];

      const formatted = builder.formatCapabilitiesEnhanced(capabilities);

      expect(formatted).toContain('google_search');
      expect(formatted).toContain('queries');
      expect(formatted).toContain('array');
      expect(formatted).toContain('required');
      expect(formatted).toContain('num');
      expect(formatted).toContain('default');
      expect(formatted).toContain('min');
      expect(formatted).toContain('max');
    });

    it('should include response schema when available', () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'test_api',
          name: 'Test API',
          category: 'api',
          status: 'available',
          responseSchema: {
            type: 'object',
            properties: {
              results: { type: 'array' },
              count: { type: 'number' },
            },
          },
        },
      ];

      const formatted = builder.formatCapabilitiesEnhanced(capabilities);

      expect(formatted).toContain('Response Schema');
      expect(formatted).toContain('results');
      expect(formatted).toContain('count');
    });

    it('should include TaskFlow examples when available', () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          examples: [
            {
              description: 'Basic search example',
              taskflow_step: {
                id: 'search_step',
                type: 'api_rest',
                config: {
                  capability_id: 'google_search',
                  method: 'POST',
                },
                params: {
                  body: {
                    queries: ['search term'],
                    num: 3,
                  },
                },
              },
            },
          ],
        },
      ];

      const formatted = builder.formatCapabilitiesEnhanced(capabilities);

      expect(formatted).toContain('TaskFlow');
      expect(formatted).toContain('Example');
      expect(formatted).toContain('search_step');
      expect(formatted).toContain('capability_id');
    });

    it('should include use cases from metadata', () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          metadata: {
            use_cases: [
              'Keyword search',
              'Multiple query search',
              'Limited result search',
            ],
          },
        },
      ];

      const formatted = builder.formatCapabilitiesEnhanced(capabilities);

      expect(formatted).toContain('Use Cases');
      expect(formatted).toContain('Keyword search');
      expect(formatted).toContain('Multiple query search');
    });

    it('should include enum constraints', () => {
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'email_api',
          name: 'Email API',
          category: 'api',
          status: 'available',
          parameters: [
            {
              name: 'priority',
              type: 'string',
              required: false,
              validation: { enum: ['low', 'normal', 'high'] },
            },
          ],
        },
      ];

      const formatted = builder.formatCapabilitiesEnhanced(capabilities);

      expect(formatted).toContain('enum');
      expect(formatted).toContain('low');
      expect(formatted).toContain('normal');
      expect(formatted).toContain('high');
    });
  });

  describe('buildFeedbackPrompt', () => {
    it('should build feedback prompt with error details', () => {
      const originalPrompt = 'Generate a workflow for searching';
      const error = new WorkflowCapabilityError(
        'Validation failed',
        {
          isValid: false,
          errors: [
            {
              code: 'MISSING_REQUIRED_PARAM',
              message: "Required parameter 'queries' is missing",
              path: 'steps[0].params.body',
            },
          ],
        },
        '{"workflow_name": "test"}',
        1
      );
      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
          parameters: [
            { name: 'queries', type: 'array', required: true },
          ],
        },
      ];

      const feedbackPrompt = builder.buildFeedbackPrompt(
        originalPrompt,
        error,
        capabilities
      );

      expect(feedbackPrompt).toContain('MISSING_REQUIRED_PARAM');
      expect(feedbackPrompt).toContain('queries');
      expect(feedbackPrompt).toContain('attempt 1');
      expect(feedbackPrompt).toContain('Google Search');
    });

    it('should include original requirements', () => {
      const originalPrompt = 'Generate a workflow for user analysis';
      const error = new WorkflowCapabilityError(
        'Validation failed',
        { isValid: false, errors: [] },
        '{}',
        2
      );

      const feedbackPrompt = builder.buildFeedbackPrompt(
        originalPrompt,
        error,
        []
      );

      expect(feedbackPrompt).toContain('user analysis');
    });

    it('should include raw content from previous attempt', () => {
      const rawContent = '{"workflow_name": "invalid_workflow", "steps": []}';
      const error = new WorkflowCapabilityError(
        'Validation failed',
        { isValid: false, errors: [] },
        rawContent,
        1
      );

      const feedbackPrompt = builder.buildFeedbackPrompt(
        'original',
        error,
        []
      );

      expect(feedbackPrompt).toContain('invalid_workflow');
    });

    it('should extract and show problem capabilities', () => {
      const error = new WorkflowCapabilityError(
        'Validation failed',
        {
          isValid: false,
          errors: [
            {
              code: 'MISSING_REQUIRED_PARAM',
              message: 'Missing parameter',
              path: 'steps[0]',
            },
          ],
        },
        '{}',
        1
      );

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'google_search',
          name: 'Google Search',
          category: 'api',
          status: 'available',
        },
        {
          id: 'email_api',
          name: 'Email API',
          category: 'api',
          status: 'available',
        },
      ];

      // If capability is specified in error, it should be highlighted
      const errorWithCapability = new WorkflowCapabilityError(
        'Validation failed',
        {
          isValid: false,
          errors: [
            {
              code: 'MISSING_REQUIRED_PARAM',
              message: 'Missing parameter',
              path: 'steps[0]',
              capability: 'google_search',
            } as any,
          ],
        },
        '{}',
        1
      );

      const feedbackPrompt = builder.buildFeedbackPrompt(
        'original',
        errorWithCapability,
        capabilities
      );

      // Should focus on the problem capability
      expect(feedbackPrompt).toContain('Google Search');
    });
  });

  describe('selectRelevantCapabilities', () => {
    it('should return all capabilities when under limit', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Search Task',
        description: 'Search for information',
        interface: { input: {}, output: {} },
      };

      const capabilities: CapabilityForPrompt[] = [
        { id: 'api_1', name: 'API 1', category: 'api', status: 'available' },
        { id: 'api_2', name: 'API 2', category: 'api', status: 'available' },
      ];

      const selected = builder.selectRelevantCapabilities(task, capabilities, 50);

      expect(selected).toHaveLength(2);
    });

    it('should limit capabilities to maxCount', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Task',
        description: 'Description',
        interface: { input: {}, output: {} },
      };

      const capabilities: CapabilityForPrompt[] = [];
      for (let i = 0; i < 100; i++) {
        capabilities.push({
          id: `api_${i}`,
          name: `API ${i}`,
          category: 'api',
          status: 'available',
        });
      }

      const selected = builder.selectRelevantCapabilities(task, capabilities, 50);

      expect(selected).toHaveLength(50);
    });

    it('should prioritize capabilities matching task name', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Google Search Task',
        description: 'Search the web',
        interface: { input: {}, output: {} },
      };

      const capabilities: CapabilityForPrompt[] = [
        { id: 'email_api', name: 'Email API', category: 'api', status: 'available' },
        { id: 'google_search', name: 'Google Search', category: 'api', status: 'available' },
        { id: 'weather_api', name: 'Weather API', category: 'api', status: 'available' },
      ];

      const selected = builder.selectRelevantCapabilities(task, capabilities, 2);

      // Google Search should be first due to name match
      expect(selected[0].id).toBe('google_search');
    });

    it('should consider use_cases in scoring', () => {
      const task: TaskGenerationRequest = {
        task_id: 'task_001',
        name: 'Email Task',
        description: 'Send an email notification',
        interface: { input: {}, output: {} },
      };

      const capabilities: CapabilityForPrompt[] = [
        {
          id: 'api_1',
          name: 'Generic API',
          category: 'api',
          status: 'available',
        },
        {
          id: 'notification_api',
          name: 'Notification API',
          category: 'api',
          status: 'available',
          metadata: {
            use_cases: ['Send email notification', 'Push notifications'],
          },
        },
      ];

      const selected = builder.selectRelevantCapabilities(task, capabilities, 1);

      expect(selected[0].id).toBe('notification_api');
    });
  });

  describe('extractKeywords', () => {
    it('should extract meaningful keywords', () => {
      const text = 'Search for user information and generate report';

      const keywords = builder.extractKeywords(text);

      expect(keywords).toContain('search');
      expect(keywords).toContain('user');
      expect(keywords).toContain('information');
      expect(keywords).toContain('generate');
      expect(keywords).toContain('report');
      // Should not include stop words
      expect(keywords).not.toContain('for');
      expect(keywords).not.toContain('and');
    });

    it('should handle hyphens and underscores', () => {
      const text = 'user-data analysis_report generation';

      const keywords = builder.extractKeywords(text);

      expect(keywords).toContain('user');
      expect(keywords).toContain('data');
      expect(keywords).toContain('analysis');
      expect(keywords).toContain('report');
      expect(keywords).toContain('generation');
    });

    it('should filter short words', () => {
      const text = 'a the of or and to be do go';

      const keywords = builder.extractKeywords(text);

      expect(keywords).toHaveLength(0);
    });

    it('should return unique keywords', () => {
      const text = 'search search search user user';

      const keywords = builder.extractKeywords(text);
      const uniqueCount = new Set(keywords).size;

      expect(keywords.length).toBe(uniqueCount);
    });
  });

  describe('calculateRelevanceScore', () => {
    it('should give highest score to name matches', () => {
      const capability: CapabilityForPrompt = {
        id: 'google_search',
        name: 'Google Search',
        description: 'Search the web',
        category: 'api',
        status: 'available',
      };

      const keywords = ['google', 'search'];
      const score = builder.calculateRelevanceScore(capability, keywords);

      // Name matches should give significant score
      expect(score).toBeGreaterThan(15);
    });

    it('should consider description matches', () => {
      const capability: CapabilityForPrompt = {
        id: 'web_api',
        name: 'Web API',
        description: 'Search the web for information',
        category: 'api',
        status: 'available',
      };

      const keywords = ['search', 'information'];
      const score = builder.calculateRelevanceScore(capability, keywords);

      expect(score).toBeGreaterThan(5);
    });

    it('should give bonus to frequent categories', () => {
      const llmCapability: CapabilityForPrompt = {
        id: 'llm_1',
        name: 'LLM API',
        description: 'Language model',
        category: 'llm',
        status: 'available',
      };

      const customCapability: CapabilityForPrompt = {
        id: 'custom_1',
        name: 'Custom API',
        description: 'Custom functionality',
        category: 'custom',
        status: 'available',
      };

      const keywords = ['api'];
      const llmScore = builder.calculateRelevanceScore(llmCapability, keywords);
      const customScore = builder.calculateRelevanceScore(customCapability, keywords);

      // LLM category should get bonus
      expect(llmScore).toBeGreaterThan(customScore);
    });

    it('should consider use_cases', () => {
      const capability: CapabilityForPrompt = {
        id: 'email_api',
        name: 'Email API',
        description: 'Send emails',
        category: 'api',
        status: 'available',
        metadata: {
          use_cases: ['Send notification email', 'Bulk email sending'],
        },
      };

      const keywords = ['notification'];
      const score = builder.calculateRelevanceScore(capability, keywords);

      expect(score).toBeGreaterThan(0);
    });

    it('should return 0 for no matches', () => {
      const capability: CapabilityForPrompt = {
        id: 'weather_api',
        name: 'Weather API',
        description: 'Get weather information',
        category: 'utility',
        status: 'available',
      };

      const keywords = ['email', 'notification'];
      const score = builder.calculateRelevanceScore(capability, keywords);

      // Only category bonus if any
      expect(score).toBeLessThanOrEqual(2);
    });
  });
});

// Import CapabilityForPrompt type for tests
import type { CapabilityForPrompt } from '../../../../src/taskflowGeneratorAgent/types/generator.js';
import { WorkflowCapabilityError } from '../../../../src/taskflowGeneratorAgent/types/errors.js';
