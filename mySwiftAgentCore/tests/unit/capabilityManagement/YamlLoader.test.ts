/**
 * YamlLoader Unit Tests
 *
 * Issue #365: Secure YAML loading for capability definitions
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import {
  YamlLoader,
  CapabilitySanitizer,
  createYamlLoader,
  createSanitizer,
} from '../../../src/capabilityManagement/loader/YamlLoader.js';
import type { CapabilityExtended } from '../../../src/shared/types/capability.types.js';

// Mock fs module
vi.mock('fs/promises');
const mockedFs = vi.mocked(fs);

describe('YamlLoader', () => {
  let loader: YamlLoader;
  const basePath = '/test/config/capabilities';

  const validYamlContent = `
id: google_search
name: Google Search
description: Search the web using Google
version: "1.0.0"
status: available
category: search
parameters:
  - name: query
    type: string
    required: true
    description: Search query
returnType: object
tags:
  - search
  - web
project: default_project
_internal:
  endpoint: https://api.google.com/search
  method: GET
  auth_type: api_key
  secret_key: GOOGLE_API_KEY
`;

  beforeEach(() => {
    vi.clearAllMocks();
    loader = new YamlLoader({ basePath });
  });

  describe('load', () => {
    it('should load and parse a valid YAML file', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);

      const capabilities = await loader.load('default_project/google_search.yaml');

      expect(capabilities).toHaveLength(1);
      expect(capabilities[0]?.id).toBe('google_search');
      expect(capabilities[0]?.name).toBe('Google Search');
    });

    it('should parse _internal section correctly', async () => {
      mockedFs.readFile.mockResolvedValueOnce(validYamlContent);

      const capabilities = await loader.load('default_project/google_search.yaml');

      expect(capabilities[0]?._internal).toBeDefined();
      expect(capabilities[0]?._internal?.endpoint).toBe('https://api.google.com/search');
      expect(capabilities[0]?._internal?.secret_key).toBe('GOOGLE_API_KEY');
    });

    it('should handle empty YAML file', async () => {
      mockedFs.readFile.mockResolvedValueOnce('');

      const capabilities = await loader.load('empty.yaml');

      expect(capabilities).toEqual([]);
    });

    it('should handle YAML file with array of capabilities', async () => {
      const multipleYaml = `
- id: cap1
  name: Capability 1
  description: First capability
  version: "1.0.0"
  status: available
  category: test
  parameters: []
  returnType: string
- id: cap2
  name: Capability 2
  description: Second capability
  version: "1.0.0"
  status: available
  category: test
  parameters: []
  returnType: string
`;
      mockedFs.readFile.mockResolvedValueOnce(multipleYaml);

      const capabilities = await loader.load('multiple.yaml');

      expect(capabilities).toHaveLength(2);
      expect(capabilities[0]?.id).toBe('cap1');
      expect(capabilities[1]?.id).toBe('cap2');
    });

    it('should throw error for invalid YAML syntax', async () => {
      const invalidYaml = `
id: test
name: invalid yaml [
`;
      mockedFs.readFile.mockResolvedValueOnce(invalidYaml);

      await expect(loader.load('invalid.yaml')).rejects.toThrow();
    });

    it('should throw error for capability missing required fields', async () => {
      const incompleteYaml = `
id: incomplete
name: Incomplete
`;
      mockedFs.readFile.mockResolvedValueOnce(incompleteYaml);

      await expect(loader.load('incomplete.yaml')).rejects.toThrow('validation failed');
    });

    it('should use JSON_SCHEMA for secure parsing (no code execution)', async () => {
      // This YAML contains a potentially dangerous tag that should be ignored
      const dangerousYaml = `
id: safe_cap
name: Safe Capability
description: This should be parsed safely
version: "1.0.0"
status: available
category: test
parameters: []
returnType: string
data: !!js/function "function() { return 'dangerous'; }"
`;
      mockedFs.readFile.mockResolvedValueOnce(dangerousYaml);

      // JSON_SCHEMA should reject or ignore the !!js/function tag
      await expect(loader.load('dangerous.yaml')).rejects.toThrow();
    });
  });

  describe('validate', () => {
    it('should validate a valid capability object', () => {
      const validCap = {
        id: 'test',
        name: 'Test',
        description: 'Test capability',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
      };

      const result = loader.validate(validCap);

      expect(result.id).toBe('test');
    });

    it('should throw for invalid capability', () => {
      const invalidCap = { id: 'test' }; // Missing required fields

      expect(() => loader.validate(invalidCap)).toThrow('validation failed');
    });
  });

  describe('loadProject', () => {
    it('should load all YAML files from a project directory', async () => {
      mockedFs.readdir.mockResolvedValueOnce([
        { name: 'cap1.yaml', isFile: () => true } as fs.Dirent,
        { name: 'cap2.yml', isFile: () => true } as fs.Dirent,
        { name: 'index.yaml', isFile: () => true } as fs.Dirent, // Should be skipped
        { name: 'subdir', isFile: () => false } as fs.Dirent, // Should be skipped
      ]);

      const cap1Yaml = `
id: cap1
name: Capability 1
description: First
version: "1.0.0"
status: available
category: test
parameters: []
returnType: string
`;
      const cap2Yaml = `
id: cap2
name: Capability 2
description: Second
version: "1.0.0"
status: available
category: test
parameters: []
returnType: string
`;

      mockedFs.readFile
        .mockResolvedValueOnce(cap1Yaml)
        .mockResolvedValueOnce(cap2Yaml);

      const result = await loader.loadProject('default_project');

      expect(result.successful).toHaveLength(2);
      expect(result.failed).toHaveLength(0);
      expect(result.totalAttempted).toBe(2);
      expect(result.hasCapabilities).toBe(true);
    });

    it('should report failed loads', async () => {
      mockedFs.readdir.mockResolvedValueOnce([
        { name: 'valid.yaml', isFile: () => true } as fs.Dirent,
        { name: 'invalid.yaml', isFile: () => true } as fs.Dirent,
      ]);

      const validYaml = `
id: valid
name: Valid
description: Valid capability
version: "1.0.0"
status: available
category: test
parameters: []
returnType: string
`;
      const invalidYaml = `id: missing_required_fields`;

      mockedFs.readFile
        .mockResolvedValueOnce(validYaml)
        .mockResolvedValueOnce(invalidYaml);

      const result = await loader.loadProject('mixed_project');

      expect(result.successful).toHaveLength(1);
      expect(result.failed).toHaveLength(1);
      expect(result.failed[0]?.file).toContain('invalid.yaml');
    });

    it('should handle directory read failure', async () => {
      mockedFs.readdir.mockRejectedValueOnce(new Error('Directory not found'));

      const result = await loader.loadProject('non_existent');

      expect(result.successful).toHaveLength(0);
      expect(result.failed).toHaveLength(1);
      expect(result.failed[0]?.error).toContain('Failed to read project directory');
    });
  });

  describe('loadIndex', () => {
    it('should load index.yaml file', async () => {
      const indexYaml = `
capabilities:
  - google_search
  - weather_api
`;
      mockedFs.readFile.mockResolvedValueOnce(indexYaml);

      const result = await loader.loadIndex('default_project');

      expect(result).toEqual(['google_search', 'weather_api']);
    });

    it('should return null if no index file exists', async () => {
      mockedFs.readFile.mockRejectedValueOnce(new Error('ENOENT'));
      mockedFs.readFile.mockRejectedValueOnce(new Error('ENOENT'));

      const result = await loader.loadIndex('no_index_project');

      expect(result).toBeNull();
    });

    it('should try both .yaml and .yml extensions', async () => {
      mockedFs.readFile.mockRejectedValueOnce(new Error('ENOENT'));
      mockedFs.readFile.mockResolvedValueOnce('capabilities:\n  - test_cap');

      const result = await loader.loadIndex('yml_project');

      expect(result).toEqual(['test_cap']);
      expect(mockedFs.readFile).toHaveBeenCalledTimes(2);
    });
  });
});

describe('CapabilitySanitizer', () => {
  let sanitizer: CapabilitySanitizer;

  const capabilityWithInternal: CapabilityExtended = {
    id: 'test',
    name: 'Test',
    description: 'Test capability',
    version: '1.0.0',
    status: 'available',
    category: 'test',
    parameters: [],
    returnType: 'string',
    _internal: {
      endpoint: 'https://secret.api.com',
      secret_key: 'SECRET_KEY',
    },
  };

  beforeEach(() => {
    sanitizer = new CapabilitySanitizer();
  });

  describe('sanitize', () => {
    it('should remove _internal section', () => {
      const result = sanitizer.sanitize(capabilityWithInternal);

      expect(result._internal).toBeUndefined();
      expect(result.id).toBe('test');
    });

    it('should preserve other fields', () => {
      const result = sanitizer.sanitize(capabilityWithInternal);

      expect(result.name).toBe('Test');
      expect(result.description).toBe('Test capability');
      expect(result.version).toBe('1.0.0');
    });

    it('should handle capability without _internal', () => {
      const capWithoutInternal: CapabilityExtended = {
        id: 'test',
        name: 'Test',
        description: 'Test',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
      };

      const result = sanitizer.sanitize(capWithoutInternal);

      expect(result.id).toBe('test');
      expect(result._internal).toBeUndefined();
    });
  });

  describe('sanitizeMany', () => {
    it('should sanitize multiple capabilities', () => {
      const capabilities = [
        capabilityWithInternal,
        { ...capabilityWithInternal, id: 'test2' },
      ];

      const results = sanitizer.sanitizeMany(capabilities);

      expect(results).toHaveLength(2);
      expect(results[0]?._internal).toBeUndefined();
      expect(results[1]?._internal).toBeUndefined();
    });
  });

  describe('hasInternal', () => {
    it('should return true if capability has _internal', () => {
      expect(sanitizer.hasInternal(capabilityWithInternal)).toBe(true);
    });

    it('should return false if capability has no _internal', () => {
      const capWithoutInternal: CapabilityExtended = {
        id: 'test',
        name: 'Test',
        description: 'Test',
        version: '1.0.0',
        status: 'available',
        category: 'test',
        parameters: [],
        returnType: 'string',
      };

      expect(sanitizer.hasInternal(capWithoutInternal)).toBe(false);
    });
  });
});

describe('Factory functions', () => {
  it('createYamlLoader should create YamlLoader instance', () => {
    const loader = createYamlLoader('/test/path');
    expect(loader).toBeInstanceOf(YamlLoader);
  });

  it('createSanitizer should create CapabilitySanitizer instance', () => {
    const sanitizer = createSanitizer();
    expect(sanitizer).toBeInstanceOf(CapabilitySanitizer);
  });
});
