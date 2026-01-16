/**
 * YamlLoader - Secure YAML loading for capability definitions
 *
 * Issue #365: Implements secure YAML parsing with SAFE_SCHEMA
 * to prevent XXE and other injection attacks.
 *
 * Security measures:
 * - Uses js-yaml SAFE_SCHEMA (no custom types, no JavaScript execution)
 * - Validates against Zod schemas after parsing
 * - Sanitizes output to remove internal details for client responses
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import yaml from 'js-yaml';
import {
  type CapabilityExtended,
  type CapabilityLoadResult,
  type PublicCapability,
  type RawCapability,
  CapabilityExtendedSchema,
} from '../../shared/types/capability.types.js';

/**
 * YAML loader configuration
 */
export interface YamlLoaderConfig {
  /** Base directory for capability files */
  basePath: string;
  /** Whether to validate schemas strictly */
  strictValidation?: boolean;
  /** File extensions to consider */
  fileExtensions?: string[];
}

/**
 * Loader strategy interface for extensibility
 */
export interface LoaderStrategy {
  load(filePath: string): Promise<RawCapability[]>;
  validate(raw: unknown): CapabilityExtended;
}

/**
 * Secure YAML loader for capability definitions
 *
 * SECURITY: Uses js-yaml SAFE_SCHEMA which:
 * - Prevents JavaScript code execution
 * - Blocks custom YAML types (!!python/object, etc.)
 * - Only allows standard YAML types (strings, numbers, arrays, objects)
 */
export class YamlLoader implements LoaderStrategy {
  private readonly config: Required<YamlLoaderConfig>;

  constructor(config: YamlLoaderConfig) {
    this.config = {
      basePath: config.basePath,
      strictValidation: config.strictValidation ?? true,
      fileExtensions: config.fileExtensions ?? ['.yaml', '.yml'],
    };
  }

  /**
   * Load a single YAML file securely
   *
   * @param filePath - Path to the YAML file
   * @returns Array of capabilities from the file
   * @throws Error if file cannot be read or parsed
   */
  async load(filePath: string): Promise<RawCapability[]> {
    const fullPath = path.resolve(this.config.basePath, filePath);
    const content = await fs.readFile(fullPath, 'utf-8');

    // SECURITY: Use JSON_SCHEMA to prevent code execution
    // JSON_SCHEMA is the safe schema that only allows standard JSON types:
    // - strings, numbers, booleans, null, arrays, objects
    // It prevents:
    // - JavaScript execution (!!js/function)
    // - Python object instantiation (!!python/object)
    // - Other potentially dangerous custom YAML types
    const parsed = yaml.load(content, {
      schema: yaml.JSON_SCHEMA,
      json: true, // Ensure JSON compatibility
      filename: fullPath, // For error messages
    });

    if (!parsed) {
      return [];
    }

    // Handle both single capability and array of capabilities
    const capabilities = Array.isArray(parsed) ? parsed : [parsed];

    return capabilities.map((cap) => this.validate(cap));
  }

  /**
   * Validate and transform raw YAML data to typed capability
   *
   * @param raw - Raw parsed YAML data
   * @returns Validated CapabilityExtended
   * @throws Error if validation fails
   */
  validate(raw: unknown): CapabilityExtended {
    const result = CapabilityExtendedSchema.safeParse(raw);

    if (!result.success) {
      const errors = result.error.errors
        .map((e) => `${e.path.join('.')}: ${e.message}`)
        .join(', ');
      throw new Error(`Capability validation failed: ${errors}`);
    }

    return result.data;
  }

  /**
   * Load all capabilities from a project directory
   *
   * @param projectPath - Relative path to the project directory
   * @returns LoadResult with successful and failed loads
   */
  async loadProject(projectPath: string): Promise<CapabilityLoadResult> {
    const fullPath = path.resolve(this.config.basePath, projectPath);
    const result: CapabilityLoadResult = {
      successful: [],
      failed: [],
      totalAttempted: 0,
      hasCapabilities: false,
    };

    try {
      const entries = await fs.readdir(fullPath, { withFileTypes: true });
      const yamlFiles = entries.filter(
        (entry) =>
          entry.isFile() &&
          this.config.fileExtensions.some((ext) => entry.name.endsWith(ext)) &&
          entry.name !== 'index.yaml' && // Skip index files
          entry.name !== 'index.yml'
      );

      result.totalAttempted = yamlFiles.length;

      for (const file of yamlFiles) {
        const filePath = path.join(projectPath, file.name);
        try {
          const capabilities = await this.load(filePath);
          result.successful.push(...capabilities);
        } catch (error) {
          result.failed.push({
            file: filePath,
            error: error instanceof Error ? error.message : String(error),
            details: error,
          });
        }
      }

      result.hasCapabilities = result.successful.length > 0;
    } catch (error) {
      result.failed.push({
        file: projectPath,
        error: `Failed to read project directory: ${error instanceof Error ? error.message : String(error)}`,
        details: error,
      });
    }

    return result;
  }

  /**
   * Load the index file for a project
   *
   * @param projectPath - Relative path to the project directory
   * @returns Array of capability IDs listed in index, or null if no index
   */
  async loadIndex(projectPath: string): Promise<string[] | null> {
    const indexPaths = ['index.yaml', 'index.yml'];

    for (const indexFile of indexPaths) {
      const fullPath = path.resolve(this.config.basePath, projectPath, indexFile);
      try {
        const content = await fs.readFile(fullPath, 'utf-8');
        const parsed = yaml.load(content, {
          schema: yaml.JSON_SCHEMA,
          json: true,
        }) as { capabilities?: string[] } | null;

        return parsed?.capabilities ?? null;
      } catch {
        // Index file doesn't exist or can't be read, continue
      }
    }

    return null;
  }
}

/**
 * Sanitizer for removing internal details from capabilities
 *
 * SECURITY: Ensures _internal section is never exposed to clients
 */
export class CapabilitySanitizer {
  /**
   * Remove _internal section from a capability
   *
   * @param capability - Raw capability with potential _internal section
   * @returns Public capability safe for client responses
   */
  sanitize(capability: RawCapability): PublicCapability {
    // Use destructuring to explicitly remove _internal
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { _internal, ...publicData } = capability;
    return publicData as PublicCapability;
  }

  /**
   * Sanitize multiple capabilities
   *
   * @param capabilities - Array of raw capabilities
   * @returns Array of public capabilities
   */
  sanitizeMany(capabilities: RawCapability[]): PublicCapability[] {
    return capabilities.map((cap) => this.sanitize(cap));
  }

  /**
   * Check if a capability has internal details
   *
   * @param capability - Capability to check
   * @returns true if _internal section exists
   */
  hasInternal(capability: RawCapability): boolean {
    return capability._internal !== undefined;
  }
}

/**
 * Factory function to create YamlLoader with default config
 */
export function createYamlLoader(basePath: string): YamlLoader {
  return new YamlLoader({ basePath });
}

/**
 * Factory function to create CapabilitySanitizer
 */
export function createSanitizer(): CapabilitySanitizer {
  return new CapabilitySanitizer();
}
