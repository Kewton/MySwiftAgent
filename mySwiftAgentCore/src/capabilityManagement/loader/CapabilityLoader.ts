/**
 * CapabilityLoader - Loads capabilities from YAML files
 *
 * Issue #372: Loads capability definitions from project directories
 *
 * Features:
 * - Load index.yaml to get capability list
 * - Load individual capability YAML files
 * - Register capabilities in CapabilityRegistry
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import yaml from 'js-yaml';
import type {
  CapabilityExtended,
  CapabilityLoadResult,
} from '../../shared/types/capability.types.js';
import type { CapabilityRegistry } from '../registry/CapabilityRegistry.js';

/**
 * Project index configuration from index.yaml
 */
interface ProjectIndex {
  capabilities?: string[];
  api_endpoints?: Record<string, unknown>;
}

/**
 * CapabilityLoader options
 */
export interface CapabilityLoaderOptions {
  /** Base path for capability configuration files */
  basePath: string;
  /** CapabilityRegistry to register capabilities */
  registry: CapabilityRegistry;
}

/**
 * CapabilityLoader - Loads and registers capabilities from YAML files
 *
 * Responsibilities:
 * - Read index.yaml to get list of capabilities
 * - Load each capability YAML file
 * - Register capabilities in the provided CapabilityRegistry
 */
export class CapabilityLoader {
  private readonly basePath: string;
  private readonly registry: CapabilityRegistry;

  constructor(options: CapabilityLoaderOptions) {
    this.basePath = options.basePath;
    this.registry = options.registry;
  }

  /**
   * Load all capabilities for a project
   *
   * @param projectId - Project identifier (directory name)
   * @returns CapabilityLoadResult with success/failure details
   */
  async loadProject(projectId: string): Promise<CapabilityLoadResult> {
    const result: CapabilityLoadResult = {
      successful: [],
      failed: [],
      totalAttempted: 0,
      hasCapabilities: false,
    };

    const projectPath = path.resolve(this.basePath, projectId);
    const indexPath = path.join(projectPath, 'index.yaml');

    // Load index.yaml to get capability list
    let capabilityIds: string[];
    try {
      const indexContent = await fs.readFile(indexPath, 'utf-8');
      const indexConfig = yaml.load(indexContent, {
        schema: yaml.JSON_SCHEMA,
        json: true,
      }) as ProjectIndex | null;

      capabilityIds = indexConfig?.capabilities ?? [];
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      result.failed.push({
        file: indexPath,
        error: `Failed to load index.yaml: ${message}`,
      });
      return result;
    }

    result.totalAttempted = capabilityIds.length;

    // Load each capability file
    for (const capabilityId of capabilityIds) {
      const capabilityPath = path.join(projectPath, `${capabilityId}.yaml`);

      try {
        const capability = await this.loadCapabilityFile(capabilityPath, projectId);
        this.registry.registerForProject(projectId, capability);
        result.successful.push(capability);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        result.failed.push({
          file: capabilityPath,
          error: message,
        });
      }
    }

    result.hasCapabilities = result.successful.length > 0;
    return result;
  }

  /**
   * Load a single capability file
   *
   * @param filePath - Path to the capability YAML file
   * @param projectId - Project identifier
   * @returns CapabilityExtended object
   */
  private async loadCapabilityFile(
    filePath: string,
    projectId: string
  ): Promise<CapabilityExtended> {
    const content = await fs.readFile(filePath, 'utf-8');

    const parsed = yaml.load(content, {
      schema: yaml.JSON_SCHEMA,
      json: true,
    }) as Record<string, unknown> | null;

    if (!parsed) {
      throw new Error(`Empty or invalid YAML file: ${filePath}`);
    }

    // Validate required fields
    if (!parsed.id || typeof parsed.id !== 'string') {
      throw new Error(`Missing or invalid 'id' field in ${filePath}`);
    }

    // Convert to CapabilityExtended
    const capability: CapabilityExtended = {
      id: parsed.id as string,
      name: (parsed.name as string) ?? parsed.id,
      description: (parsed.description as string) ?? '',
      version: (parsed.version as string) ?? '1.0.0',
      status: (parsed.status as CapabilityExtended['status']) ?? 'available',
      category: (parsed.category as string) ?? 'general',
      parameters: (parsed.parameters as CapabilityExtended['parameters']) ?? [],
      returnType: (parsed.returnType as CapabilityExtended['returnType']) ?? 'object',
      examples: parsed.examples as CapabilityExtended['examples'],
      tags: parsed.tags as string[],
      metadata: parsed.metadata as Record<string, unknown>,
      project: projectId,
      _internal: parsed._internal as CapabilityExtended['_internal'],
    };

    return capability;
  }

  /**
   * Load all projects in the base path
   *
   * Scans the base path for directories containing index.yaml
   * and loads all capabilities from each project.
   *
   * @returns Map of projectId to CapabilityLoadResult
   */
  async loadAllProjects(): Promise<Map<string, CapabilityLoadResult>> {
    const results = new Map<string, CapabilityLoadResult>();

    try {
      const entries = await fs.readdir(this.basePath, { withFileTypes: true });

      for (const entry of entries) {
        if (entry.isDirectory()) {
          const indexPath = path.join(this.basePath, entry.name, 'index.yaml');

          // Check if index.yaml exists
          try {
            await fs.access(indexPath);
            const result = await this.loadProject(entry.name);
            results.set(entry.name, result);
          } catch {
            // Skip directories without index.yaml
          }
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to scan projects in ${this.basePath}: ${message}`);
    }

    return results;
  }
}

/**
 * Factory function to create CapabilityLoader
 *
 * @param basePath - Base path for capability configuration files
 * @param registry - CapabilityRegistry to register capabilities
 * @returns CapabilityLoader instance
 */
export function createCapabilityLoader(
  basePath: string,
  registry: CapabilityRegistry
): CapabilityLoader {
  return new CapabilityLoader({ basePath, registry });
}
