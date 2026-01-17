/**
 * EndpointConfigManager - Manages API endpoint configurations
 *
 * Issue #372: Provides endpoint configuration loading and environment variable resolution
 *
 * Features:
 * - Load api_endpoints from project index.yaml
 * - Resolve environment variables with ${VAR:-default} pattern
 * - Cache configurations for performance
 */

import * as fs from 'fs/promises';
import * as path from 'path';
import yaml from 'js-yaml';
import type {
  ApiEndpointsConfig,
  EndpointConfigManagerOptions,
  IEndpointConfigManager,
  ProjectIndexConfig,
} from './types.js';
import { ProjectIndexConfigSchema } from './types.js';

/**
 * EndpointConfigManager - Manages endpoint configuration loading and caching
 *
 * Responsibilities:
 * - Load and parse index.yaml files for projects
 * - Resolve environment variables in configuration values
 * - Cache loaded configurations for performance
 */
export class EndpointConfigManager implements IEndpointConfigManager {
  private readonly basePath: string;
  private readonly enableCache: boolean;
  private readonly cache: Map<string, ApiEndpointsConfig>;

  constructor(options: EndpointConfigManagerOptions) {
    this.basePath = options.basePath;
    this.enableCache = options.enableCache ?? true;
    this.cache = new Map();
  }

  /**
   * Load endpoint configurations for a project
   *
   * Reads the project's index.yaml file and extracts the api_endpoints section.
   * Resolves any environment variables in the base_url values.
   *
   * @param projectId - Project identifier (directory name)
   * @returns ApiEndpointsConfig with resolved environment variables
   * @throws Error if index.yaml cannot be read or parsed
   */
  async loadProjectEndpoints(projectId: string): Promise<ApiEndpointsConfig> {
    // Check cache first
    if (this.enableCache) {
      const cached = this.cache.get(projectId);
      if (cached) {
        return cached;
      }
    }

    const indexPath = path.resolve(this.basePath, projectId, 'index.yaml');

    try {
      const content = await fs.readFile(indexPath, 'utf-8');

      // Parse YAML with JSON_SCHEMA for security
      const parsed = yaml.load(content, {
        schema: yaml.JSON_SCHEMA,
        json: true,
        filename: indexPath,
      }) as unknown;

      // Validate parsed content
      const validationResult = ProjectIndexConfigSchema.safeParse(parsed);

      if (!validationResult.success) {
        throw new Error(
          `Invalid index.yaml format: ${validationResult.error.errors.map((e) => e.message).join(', ')}`
        );
      }

      const indexConfig: ProjectIndexConfig = validationResult.data;

      // Extract and resolve api_endpoints
      const apiEndpoints: ApiEndpointsConfig = {};

      if (indexConfig.api_endpoints) {
        for (const [key, endpoint] of Object.entries(indexConfig.api_endpoints)) {
          apiEndpoints[key] = {
            ...endpoint,
            base_url: this.resolveEnvVars(endpoint.base_url),
          };
        }
      }

      // Cache the result
      if (this.enableCache) {
        this.cache.set(projectId, apiEndpoints);
      }

      return apiEndpoints;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      throw new Error(`Failed to load endpoint configuration for project '${projectId}': ${message}`);
    }
  }

  /**
   * Resolve environment variables in a string
   *
   * Supports the pattern: ${VAR_NAME:-default_value}
   * - VAR_NAME: Environment variable name
   * - default_value: Value to use if VAR_NAME is not set (optional)
   *
   * @param value - String potentially containing environment variable patterns
   * @returns String with environment variables resolved
   */
  resolveEnvVars(value: string): string {
    // Pattern: ${VAR_NAME} or ${VAR_NAME:-default_value}
    const pattern = /\$\{([^}]+)\}/g;

    return value.replace(pattern, (_match, content: string) => {
      // Split on first :- to separate variable name from default value
      const separatorIndex = content.indexOf(':-');

      if (separatorIndex === -1) {
        // No default value specified: ${VAR_NAME}
        const varName = content.trim();
        const envValue = process.env[varName];
        return envValue ?? '';
      }

      // Has default value: ${VAR_NAME:-default_value}
      const varName = content.substring(0, separatorIndex).trim();
      const defaultValue = content.substring(separatorIndex + 2);

      const envValue = process.env[varName];
      return envValue !== undefined && envValue !== '' ? envValue : defaultValue;
    });
  }

  /**
   * Clear cached configurations
   *
   * Use this when configuration files have been modified
   * or environment variables have changed.
   */
  clearCache(): void {
    this.cache.clear();
  }
}

/**
 * Factory function to create EndpointConfigManager
 *
 * @param basePath - Base path for configuration files
 * @returns EndpointConfigManager instance
 */
export function createEndpointConfigManager(basePath: string): EndpointConfigManager {
  return new EndpointConfigManager({ basePath });
}
