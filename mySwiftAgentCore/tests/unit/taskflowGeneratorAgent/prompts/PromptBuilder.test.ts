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
import {
  isCapabilityForPrompt,
  toCapabilitiesForPrompt,
} from '../../../../src/taskflowGeneratorAgent/prompts/PromptBuilder.js';

/**
 * Issue #382: Type Guard Functions Tests
 *
 * Tests for type-safe conversion from Capability to CapabilityForPrompt
 */
describe('Issue #382: Type Guard Functions', () => {
  describe('isCapabilityForPrompt', () => {
    it('TC-001: should return true for capability with responseSchema', () => {
      const capability: Capability = {
        id: 'test_api',
        name: 'Test API',
        category: 'api',
        status: 'available',
      };
      // Add responseSchema to make it CapabilityForPrompt
      const capWithSchema = {
        ...capability,
        responseSchema: {
          type: 'object',
          properties: { result: { type: 'string' } },
        },
      } as CapabilityForPrompt;

      expect(isCapabilityForPrompt(capWithSchema as Capability)).toBe(true);
    });

    it('TC-002: should return true for capability with validation constraints', () => {
      const capability: Capability = {
        id: 'test_api',
        name: 'Test API',
        category: 'api',
        status: 'available',
        parameters: [
          {
            name: 'count',
            type: 'number',
            required: false,
            validation: { min: 1, max: 100 },
          },
        ],
      };

      expect(isCapabilityForPrompt(capability)).toBe(true);
    });

    it('TC-003: should return false for basic capability without enhanced fields', () => {
      const capability: Capability = {
        id: 'basic_api',
        name: 'Basic API',
        category: 'api',
        status: 'available',
        parameters: [
          { name: 'input', type: 'string', required: true },
        ],
      };

      expect(isCapabilityForPrompt(capability)).toBe(false);
    });

    it('TC-003b: should return false for capability with no parameters', () => {
      const capability: Capability = {
        id: 'no_params_api',
        name: 'No Params API',
        category: 'api',
        status: 'available',
      };

      expect(isCapabilityForPrompt(capability)).toBe(false);
    });

    it('TC-003c: should return false for capability with empty parameters array', () => {
      const capability: Capability = {
        id: 'empty_params_api',
        name: 'Empty Params API',
        category: 'api',
        status: 'available',
        parameters: [],
      };

      expect(isCapabilityForPrompt(capability)).toBe(false);
    });
  });

  describe('toCapabilitiesForPrompt', () => {
    it('TC-004: should convert Capability array to CapabilityForPrompt array', () => {
      const capabilities: Capability[] = [
        {
          id: 'basic_api',
          name: 'Basic API',
          category: 'api',
          status: 'available',
        },
        {
          id: 'enhanced_api',
          name: 'Enhanced API',
          category: 'api',
          status: 'available',
          parameters: [
            {
              name: 'num',
              type: 'number',
              required: false,
              validation: { min: 1, max: 10 },
            },
          ],
        },
      ];

      const result = toCapabilitiesForPrompt(capabilities);

      expect(result).toHaveLength(2);
      expect(result[0].id).toBe('basic_api');
      expect(result[1].id).toBe('enhanced_api');
      // All items should be assignable to CapabilityForPrompt
      result.forEach((cap) => {
        expect(cap).toHaveProperty('id');
        expect(cap).toHaveProperty('name');
        expect(cap).toHaveProperty('category');
        expect(cap).toHaveProperty('status');
      });
    });

    it('TC-004b: should preserve enhanced fields during conversion', () => {
      const capabilities: Capability[] = [
        {
          id: 'with_schema',
          name: 'With Schema',
          category: 'api',
          status: 'available',
        } as Capability,
      ];
      // Add responseSchema after creation
      (capabilities[0] as Record<string, unknown>).responseSchema = {
        type: 'object',
        properties: { data: { type: 'string' } },
      };

      const result = toCapabilitiesForPrompt(capabilities);

      expect(result[0]).toHaveProperty('responseSchema');
    });

    it('TC-004c: should handle empty array', () => {
      const result = toCapabilitiesForPrompt([]);

      expect(result).toHaveLength(0);
      expect(Array.isArray(result)).toBe(true);
    });
  });
});

/**
 * Issue #382: buildSystemPromptWithCapabilities Tests
 *
 * Tests that buildSystemPrompt uses formatCapabilitiesEnhanced
 */
describe('Issue #382: buildSystemPromptWithCapabilities modification', () => {
  let builder: PromptBuilder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  it('TC-005: should include validation constraints in system prompt (via formatCapabilitiesEnhanced)', () => {
    const capabilities: Capability[] = [
      {
        id: 'google_search',
        name: 'Google Search',
        description: 'Search the web',
        category: 'api',
        status: 'available',
        parameters: [
          {
            name: 'num',
            type: 'number',
            required: false,
            description: 'Number of results',
            defaultValue: 10,
            validation: { min: 1, max: 100 },
          },
          {
            name: 'safe',
            type: 'string',
            required: false,
            validation: { enum: ['off', 'medium', 'high'] },
          },
        ],
      },
    ];

    const prompt = builder.buildSystemPrompt(capabilities);

    // Should include validation constraints from formatCapabilitiesEnhanced
    expect(prompt).toContain('min');
    expect(prompt).toContain('max');
    expect(prompt).toContain('enum');
    expect(prompt).toContain('default');
  });

  it('TC-006: should include responseSchema in system prompt (via formatCapabilitiesEnhanced)', () => {
    // Create a capability with responseSchema
    const capabilityWithSchema: CapabilityForPrompt = {
      id: 'api_with_schema',
      name: 'API with Schema',
      category: 'api',
      status: 'available',
      responseSchema: {
        type: 'object',
        properties: {
          results: { type: 'array' },
          total: { type: 'number' },
        },
      },
    };

    const prompt = builder.buildSystemPrompt([capabilityWithSchema as Capability]);

    // Should include Response Schema section from formatCapabilitiesEnhanced
    expect(prompt).toContain('Response Schema');
    expect(prompt).toContain('results');
    expect(prompt).toContain('total');
  });

  it('TC-007: should maintain backward compatibility with basic capabilities', () => {
    const basicCapabilities: Capability[] = [
      {
        id: 'simple_api',
        name: 'Simple API',
        description: 'A simple API',
        category: 'api',
        status: 'available',
        parameters: [
          { name: 'input', type: 'string', required: true, description: 'Input value' },
        ],
      },
    ];

    const prompt = builder.buildSystemPrompt(basicCapabilities);

    // Should still include basic capability info
    expect(prompt).toContain('Simple API');
    expect(prompt).toContain('simple_api');
    expect(prompt).toContain('input');
    expect(prompt).toContain('required');
    // Should not throw errors
  });

  it('TC-008: should include use cases in system prompt when available', () => {
    const capabilityWithUseCases: CapabilityForPrompt = {
      id: 'search_api',
      name: 'Search API',
      category: 'api',
      status: 'available',
      metadata: {
        use_cases: [
          'Web search queries',
          'Document retrieval',
        ],
      },
    };

    const prompt = builder.buildSystemPrompt([capabilityWithUseCases as Capability]);

    expect(prompt).toContain('Use Cases');
    expect(prompt).toContain('Web search queries');
    expect(prompt).toContain('Document retrieval');
  });
});

/**
 * Issue #392: Test cases for workflow name generation edge cases
 * Ensures workflow names are not duplicated (e.g., task_task_001_task_001)
 */
describe('Issue #392: Workflow name generation edge cases', () => {
  let builder: PromptBuilder;

  beforeEach(() => {
    builder = new PromptBuilder();
  });

  it('should not duplicate task_id in workflow name when task name equals task_id', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: 'task_001',  // Same as task_id
      description: 'Test task',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Should use task_id only, not task_001_task_001
    expect(prompt).toContain('workflow_name: "task_001"');
    expect(prompt).not.toContain('task_001_task_001');
  });

  it('should not duplicate task_id in workflow name when task name contains task_id', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: 'Task_001 Search',  // Contains task_id
      description: 'Test task',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Should use task_id only
    expect(prompt).toContain('workflow_name: "task_001"');
    expect(prompt).not.toContain('task_001_search_task_001');
  });

  it('should generate proper workflow name when task name is meaningful', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: 'Gmail Search',
      description: 'Search emails',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Should generate gmail_search_task_001
    expect(prompt).toContain('workflow_name: "gmail_search_task_001"');
  });

  it('should fallback to task_id when task name is empty', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: '',
      description: 'Test task',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Should use task_id only
    expect(prompt).toContain('workflow_name: "task_001"');
  });

  it('should fallback to task_id when task name is generic "task"', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: 'Task',
      description: 'Test task',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Should use task_id only, not task_task_001
    expect(prompt).toContain('workflow_name: "task_001"');
    expect(prompt).not.toContain('task_task_001');
  });

  it('should handle Japanese task names correctly', () => {
    const task: TaskGenerationRequest = {
      task_id: 'task_001',
      name: 'Gmail検索',
      description: 'メールを検索',
      interface: { input: {}, output: {} },
    };

    const prompt = builder.buildUserPrompt(task);

    // Japanese characters are stripped, only 'gmail' remains
    expect(prompt).toContain('workflow_name: "gmail_task_001"');
  });
});
