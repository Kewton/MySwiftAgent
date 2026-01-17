/**
 * CapabilityLoader Unit Tests
 *
 * Issue #372: Tests for loading capabilities from YAML files
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fs from 'fs/promises';
import * as path from 'path';
import { CapabilityLoader, createCapabilityLoader } from '../../../../src/capabilityManagement/loader/CapabilityLoader.js';
import { createCapabilityRegistry } from '../../../../src/capabilityManagement/registry/CapabilityRegistry.js';
import type { CapabilityRegistry } from '../../../../src/capabilityManagement/registry/CapabilityRegistry.js';

// Mock fs module
vi.mock('fs/promises');

describe('CapabilityLoader', () => {
  let registry: CapabilityRegistry;
  let loader: CapabilityLoader;
  const testBasePath = '/test/capabilities';

  beforeEach(() => {
    vi.clearAllMocks();
    registry = createCapabilityRegistry();
    loader = createCapabilityLoader(testBasePath, registry);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('loadProject', () => {
    it('should load capabilities from index.yaml and register them', async () => {
      // Arrange: Mock index.yaml
      const indexContent = `
capabilities:
  - google_search
  - gmail_send
`;
      const googleSearchContent = `
id: google_search
name: Google Search
description: Search the web
version: "1.0.0"
status: available
category: search
parameters: []
returnType: object
_internal:
  endpoint: /v1/utility/google_search
  method: POST
`;
      const gmailSendContent = `
id: gmail_send
name: Gmail Send
description: Send email via Gmail
version: "1.0.0"
status: available
category: email
parameters: []
returnType: object
_internal:
  endpoint: /v1/utility/gmail/send
  method: POST
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('google_search.yaml')) {
          return googleSearchContent;
        }
        if (pathStr.endsWith('gmail_send.yaml')) {
          return gmailSendContent;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const result = await loader.loadProject('default_project');

      // Assert
      expect(result.hasCapabilities).toBe(true);
      expect(result.successful.length).toBe(2);
      expect(result.failed.length).toBe(0);
      expect(result.totalAttempted).toBe(2);

      // Verify capabilities are registered
      const googleSearch = registry.getCapability('default_project', 'google_search');
      expect(googleSearch).toBeDefined();
      expect(googleSearch?.name).toBe('Google Search');
      expect(googleSearch?._internal?.endpoint).toBe('/v1/utility/google_search');

      const gmailSend = registry.getCapability('default_project', 'gmail_send');
      expect(gmailSend).toBeDefined();
      expect(gmailSend?.name).toBe('Gmail Send');
    });

    it('should handle missing index.yaml gracefully', async () => {
      // Arrange
      vi.mocked(fs.readFile).mockRejectedValue(new Error('ENOENT: no such file or directory'));

      // Act
      const result = await loader.loadProject('missing_project');

      // Assert
      expect(result.hasCapabilities).toBe(false);
      expect(result.successful.length).toBe(0);
      expect(result.failed.length).toBe(1);
      expect(result.failed[0].error).toContain('Failed to load index.yaml');
    });

    it('should handle missing capability files gracefully', async () => {
      // Arrange
      const indexContent = `
capabilities:
  - existing_capability
  - missing_capability
`;
      const existingContent = `
id: existing_capability
name: Existing Capability
description: Test
version: "1.0.0"
status: available
category: test
parameters: []
returnType: object
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('existing_capability.yaml')) {
          return existingContent;
        }
        throw new Error(`ENOENT: no such file or directory: ${pathStr}`);
      });

      // Act
      const result = await loader.loadProject('test_project');

      // Assert
      expect(result.hasCapabilities).toBe(true);
      expect(result.successful.length).toBe(1);
      expect(result.failed.length).toBe(1);
      expect(result.totalAttempted).toBe(2);

      // Verify existing capability is registered
      const existing = registry.getCapability('test_project', 'existing_capability');
      expect(existing).toBeDefined();
    });

    it('should handle empty capabilities list', async () => {
      // Arrange
      const indexContent = `
capabilities: []
`;
      vi.mocked(fs.readFile).mockResolvedValue(indexContent);

      // Act
      const result = await loader.loadProject('empty_project');

      // Assert
      expect(result.hasCapabilities).toBe(false);
      expect(result.successful.length).toBe(0);
      expect(result.failed.length).toBe(0);
      expect(result.totalAttempted).toBe(0);
    });

    it('should handle index.yaml without capabilities key', async () => {
      // Arrange
      const indexContent = `
api_endpoints:
  expert_agent:
    base_url: "http://localhost:8004"
`;
      vi.mocked(fs.readFile).mockResolvedValue(indexContent);

      // Act
      const result = await loader.loadProject('no_capabilities_project');

      // Assert
      expect(result.hasCapabilities).toBe(false);
      expect(result.successful.length).toBe(0);
      expect(result.totalAttempted).toBe(0);
    });

    it('should validate capability has required id field', async () => {
      // Arrange
      const indexContent = `
capabilities:
  - invalid_capability
`;
      const invalidContent = `
name: Invalid Capability
description: Missing id field
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('invalid_capability.yaml')) {
          return invalidContent;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const result = await loader.loadProject('test_project');

      // Assert
      expect(result.hasCapabilities).toBe(false);
      expect(result.successful.length).toBe(0);
      expect(result.failed.length).toBe(1);
      expect(result.failed[0].error).toContain("Missing or invalid 'id' field");
    });

    it('should set project field on loaded capabilities', async () => {
      // Arrange
      const indexContent = `
capabilities:
  - test_capability
`;
      const capabilityContent = `
id: test_capability
name: Test Capability
description: Test
version: "1.0.0"
status: available
category: test
parameters: []
returnType: object
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('test_capability.yaml')) {
          return capabilityContent;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const result = await loader.loadProject('my_project');

      // Assert
      expect(result.successful[0].project).toBe('my_project');
    });

    it('should use default values for optional fields', async () => {
      // Arrange
      const indexContent = `
capabilities:
  - minimal_capability
`;
      const minimalContent = `
id: minimal_capability
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('minimal_capability.yaml')) {
          return minimalContent;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const result = await loader.loadProject('test_project');

      // Assert
      const capability = result.successful[0];
      expect(capability.id).toBe('minimal_capability');
      expect(capability.name).toBe('minimal_capability'); // Uses id as default
      expect(capability.description).toBe('');
      expect(capability.version).toBe('1.0.0');
      expect(capability.status).toBe('available');
      expect(capability.category).toBe('general');
      expect(capability.parameters).toEqual([]);
      expect(capability.returnType).toBe('object');
    });
  });

  describe('loadAllProjects', () => {
    it('should load capabilities from all project directories', async () => {
      // Arrange
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'project1', isDirectory: () => true } as fs.Dirent,
        { name: 'project2', isDirectory: () => true } as fs.Dirent,
        { name: 'not_a_dir.txt', isDirectory: () => false } as fs.Dirent,
      ]);

      vi.mocked(fs.access).mockResolvedValue(undefined);

      const project1Index = `
capabilities:
  - cap1
`;
      const project2Index = `
capabilities:
  - cap2
`;
      const cap1Content = `
id: cap1
name: Capability 1
description: Test
version: "1.0.0"
status: available
category: test
parameters: []
returnType: object
`;
      const cap2Content = `
id: cap2
name: Capability 2
description: Test
version: "1.0.0"
status: available
category: test
parameters: []
returnType: object
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.includes('project1') && pathStr.endsWith('index.yaml')) {
          return project1Index;
        }
        if (pathStr.includes('project2') && pathStr.endsWith('index.yaml')) {
          return project2Index;
        }
        if (pathStr.endsWith('cap1.yaml')) {
          return cap1Content;
        }
        if (pathStr.endsWith('cap2.yaml')) {
          return cap2Content;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const results = await loader.loadAllProjects();

      // Assert
      expect(results.size).toBe(2);
      expect(results.get('project1')?.successful.length).toBe(1);
      expect(results.get('project2')?.successful.length).toBe(1);

      // Verify capabilities are registered
      const cap1 = registry.getCapability('project1', 'cap1');
      const cap2 = registry.getCapability('project2', 'cap2');
      expect(cap1).toBeDefined();
      expect(cap2).toBeDefined();
    });

    it('should skip directories without index.yaml', async () => {
      // Arrange
      vi.mocked(fs.readdir).mockResolvedValue([
        { name: 'with_index', isDirectory: () => true } as fs.Dirent,
        { name: 'without_index', isDirectory: () => true } as fs.Dirent,
      ]);

      vi.mocked(fs.access).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.includes('with_index')) {
          return undefined;
        }
        throw new Error('ENOENT');
      });

      const indexContent = `
capabilities:
  - test_cap
`;
      const capContent = `
id: test_cap
name: Test
description: Test
version: "1.0.0"
status: available
category: test
parameters: []
returnType: object
`;

      vi.mocked(fs.readFile).mockImplementation(async (filePath) => {
        const pathStr = filePath.toString();
        if (pathStr.endsWith('index.yaml')) {
          return indexContent;
        }
        if (pathStr.endsWith('test_cap.yaml')) {
          return capContent;
        }
        throw new Error(`File not found: ${pathStr}`);
      });

      // Act
      const results = await loader.loadAllProjects();

      // Assert
      expect(results.size).toBe(1);
      expect(results.has('with_index')).toBe(true);
      expect(results.has('without_index')).toBe(false);
    });
  });

  describe('createCapabilityLoader factory', () => {
    it('should create a CapabilityLoader instance', () => {
      // Act
      const loader = createCapabilityLoader('/test/path', registry);

      // Assert
      expect(loader).toBeInstanceOf(CapabilityLoader);
    });
  });
});
