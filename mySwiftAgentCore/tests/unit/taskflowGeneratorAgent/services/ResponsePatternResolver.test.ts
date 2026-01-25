/**
 * ResponsePatternResolver Unit Tests
 *
 * Issue #399: API response schema consideration for workflow generation
 *
 * Tests:
 * - YAML loading with safeLoad (security)
 * - Pattern resolution by capability ID
 * - Mapping hint generation
 * - Graceful degradation on load errors
 * - Validation of pattern config
 * - Caching behavior
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import * as fs from 'fs/promises';
import {
  ResponsePatternResolver,
  createResponsePatternResolver,
  type ResponsePattern,
  type ResponsePatternsConfig,
} from '../../../../src/taskflowGeneratorAgent/services/ResponsePatternResolver.js';

// Mock fs module
vi.mock('fs/promises');
const mockedFs = vi.mocked(fs);

describe('ResponsePatternResolver', () => {
  let resolver: ResponsePatternResolver;

  const validYamlContent = `
version: "1.0"
patterns:
  json_output_agent:
    pattern: wrapped
    wrapperField: result
    description: "LLM output wrapped in 'result' field"
    mappingNote: "Access via steps.{step_id}.result.{field}"
    example:
      input:
        user_input: "Generate email subject"
      output:
        result:
          subject: "Meeting Notice"
        type: "jsonOutput"

  google_search:
    pattern: direct
    description: "Search results returned directly"
    mappingNote: "Access via steps.{step_id}.{field}"
    example:
      output:
        search_results:
          - title: "Result 1"
            url: "https://example.com"
        status: "success"

  gmail_send:
    pattern: direct
    description: "Send result returned directly"
    mappingNote: "Access via steps.{step_id}.{field}"
    example:
      output:
        message_id: "abc123"
        status: "sent"
`;

  beforeEach(() => {
    vi.clearAllMocks();
    resolver = new ResponsePatternResolver('/test/config/response-patterns.yaml');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('load()', () => {
    it('should load and parse valid YAML file using safeLoad', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);

      await resolver.load();

      expect(resolver.getPatternCount()).toBe(3);
    });

    it('should use js-yaml safeLoad for security (reject dangerous YAML)', async () => {
      // YAML with potentially dangerous !!js/function tag
      const dangerousYaml = `
version: "1.0"
patterns:
  test_api:
    pattern: direct
    description: "Test API"
    mappingNote: "Test mapping"
    dangerous: !!js/function "function() { return 'dangerous'; }"
    example:
      output:
        result: "test"
`;
      mockedFs.readFile.mockResolvedValueOnce(dangerousYaml);

      // safeLoad should reject or ignore dangerous tags
      await resolver.load();

      // Should gracefully degrade - patterns should not be loaded or error handled
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should only load once (caching)', async () => {
      mockedFs.readFile.mockResolvedValue(validYamlContent);

      await resolver.load();
      await resolver.load();
      await resolver.load();

      expect(mockedFs.readFile).toHaveBeenCalledTimes(1);
    });

    it('should gracefully degrade on file not found error', async () => {
      mockedFs.readFile.mockRejectedValueOnce(new Error('ENOENT: no such file'));

      // Should not throw
      await expect(resolver.load()).resolves.toBeUndefined();

      // Should have 0 patterns but still be considered loaded
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should gracefully degrade on invalid YAML syntax', async () => {
      const invalidYaml = `
version: "1.0"
patterns: [
  invalid yaml syntax
`;
      mockedFs.readFile.mockResolvedValueOnce(invalidYaml);

      // Should not throw
      await expect(resolver.load()).resolves.toBeUndefined();

      // Should have 0 patterns
      expect(resolver.getPatternCount()).toBe(0);
    });
  });

  describe('validateConfig()', () => {
    it('should throw error for missing patterns field', async () => {
      const invalidConfig = `
version: "1.0"
`;
      mockedFs.readFile.mockResolvedValueOnce(invalidConfig);

      await resolver.load();
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should throw error for invalid pattern type', async () => {
      const invalidPatternType = `
version: "1.0"
patterns:
  test_api:
    pattern: invalid_type
    description: "Test"
    mappingNote: "Test"
    example:
      output:
        result: "test"
`;
      mockedFs.readFile.mockResolvedValueOnce(invalidPatternType);

      await resolver.load();
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should throw error for wrapped pattern without wrapperField', async () => {
      const missingWrapperField = `
version: "1.0"
patterns:
  test_api:
    pattern: wrapped
    description: "Test"
    mappingNote: "Test"
    example:
      output:
        result: "test"
`;
      mockedFs.readFile.mockResolvedValueOnce(missingWrapperField);

      await resolver.load();
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should accept pattern without version (with warning)', async () => {
      const noVersion = `
patterns:
  test_api:
    pattern: direct
    description: "Test"
    mappingNote: "Test"
    example:
      output:
        result: "test"
`;
      mockedFs.readFile.mockResolvedValueOnce(noVersion);

      await resolver.load();
      expect(resolver.getPatternCount()).toBe(1);
    });
  });

  describe('resolvePattern()', () => {
    beforeEach(async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);
      await resolver.load();
    });

    it('should resolve pattern for json_output_agent', () => {
      const pattern = resolver.resolvePattern('json_output_agent');

      expect(pattern).toBeDefined();
      expect(pattern?.apiId).toBe('json_output_agent');
      expect(pattern?.pattern).toBe('wrapped');
      expect(pattern?.wrapperField).toBe('result');
    });

    it('should resolve pattern for google_search', () => {
      const pattern = resolver.resolvePattern('google_search');

      expect(pattern).toBeDefined();
      expect(pattern?.pattern).toBe('direct');
      expect(pattern?.wrapperField).toBeUndefined();
    });

    it('should resolve pattern for gmail_send', () => {
      const pattern = resolver.resolvePattern('gmail_send');

      expect(pattern).toBeDefined();
      expect(pattern?.pattern).toBe('direct');
    });

    it('should return undefined for unknown capability', () => {
      const pattern = resolver.resolvePattern('unknown_api');

      expect(pattern).toBeUndefined();
    });

    it('should include example in resolved pattern', () => {
      const pattern = resolver.resolvePattern('json_output_agent');

      expect(pattern?.example).toBeDefined();
      expect(pattern?.example.output).toBeDefined();
      expect(pattern?.example.output.result).toBeDefined();
    });
  });

  describe('getMappingHint()', () => {
    beforeEach(async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);
      await resolver.load();
    });

    it('should return warning hint for wrapped pattern', () => {
      const hint = resolver.getMappingHint('json_output_agent');

      expect(hint).toContain('result');
      expect(hint).toContain('steps.{step_id}.result.{field}');
    });

    it('should return direct access hint for direct pattern', () => {
      const hint = resolver.getMappingHint('google_search');

      expect(hint).toContain('Direct access');
      expect(hint).toContain('steps.{step_id}.{field}');
    });

    it('should return undefined for unknown capability', () => {
      const hint = resolver.getMappingHint('unknown_api');

      expect(hint).toBeUndefined();
    });
  });

  describe('getPatternCount()', () => {
    it('should return 0 before load', () => {
      expect(resolver.getPatternCount()).toBe(0);
    });

    it('should return correct count after load', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);
      await resolver.load();

      expect(resolver.getPatternCount()).toBe(3);
    });
  });

  describe('isLoaded()', () => {
    it('should return false before load', () => {
      expect(resolver.isLoaded()).toBe(false);
    });

    it('should return true after successful load', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);
      await resolver.load();

      expect(resolver.isLoaded()).toBe(true);
    });

    it('should return true after failed load (graceful degradation)', async () => {
      mockedFs.readFile.mockRejectedValueOnce(new Error('File not found'));
      await resolver.load();

      expect(resolver.isLoaded()).toBe(true);
    });
  });

  describe('getAllPatterns()', () => {
    it('should return empty array before load', () => {
      const patterns = resolver.getAllPatterns();
      expect(patterns).toEqual([]);
    });

    it('should return all patterns after load', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);
      await resolver.load();

      const patterns = resolver.getAllPatterns();
      expect(patterns).toHaveLength(3);
      expect(patterns.map(p => p.apiId)).toContain('json_output_agent');
      expect(patterns.map(p => p.apiId)).toContain('google_search');
      expect(patterns.map(p => p.apiId)).toContain('gmail_send');
    });
  });
});

describe('createResponsePatternResolver()', () => {
  it('should create ResponsePatternResolver instance with default path', () => {
    const resolver = createResponsePatternResolver();
    expect(resolver).toBeInstanceOf(ResponsePatternResolver);
  });

  it('should create ResponsePatternResolver instance with custom path', () => {
    const resolver = createResponsePatternResolver('/custom/path.yaml');
    expect(resolver).toBeInstanceOf(ResponsePatternResolver);
  });
});

describe('ResponsePattern type', () => {
  it('should have correct shape for wrapped pattern', () => {
    const wrappedPattern: ResponsePattern = {
      apiId: 'json_output_agent',
      pattern: 'wrapped',
      wrapperField: 'result',
      description: 'Test description',
      mappingNote: 'Test mapping note',
      example: {
        output: { result: { data: 'test' } },
      },
    };

    expect(wrappedPattern.pattern).toBe('wrapped');
    expect(wrappedPattern.wrapperField).toBe('result');
  });

  it('should have correct shape for direct pattern', () => {
    const directPattern: ResponsePattern = {
      apiId: 'google_search',
      pattern: 'direct',
      description: 'Test description',
      mappingNote: 'Test mapping note',
      example: {
        output: { search_results: [] },
      },
    };

    expect(directPattern.pattern).toBe('direct');
    expect(directPattern.wrapperField).toBeUndefined();
  });
});

describe('ResponsePatternsConfig type', () => {
  it('should have correct shape', () => {
    const config: ResponsePatternsConfig = {
      version: '1.0',
      patterns: {
        test_api: {
          pattern: 'direct',
          description: 'Test',
          mappingNote: 'Test',
          example: {
            output: { result: 'test' },
          },
        },
      },
    };

    expect(config.version).toBe('1.0');
    expect(config.patterns.test_api).toBeDefined();
  });
});
