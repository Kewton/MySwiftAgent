/**
 * ResponsePatternResolver - Resolves API response patterns for workflow generation
 *
 * Issue #399: API response schema consideration for workflow generation
 *
 * Features:
 * - YAML loading with safeLoad (security)
 * - Pattern resolution by capability ID
 * - Mapping hint generation for LLM prompts
 * - Graceful degradation on load errors
 * - Caching for performance
 *
 * Security:
 * - Uses js-yaml safeLoad (JSON_SCHEMA) to prevent YAML injection attacks
 * - Validates pattern config structure
 */

import * as yaml from 'js-yaml';
import { readFile } from 'fs/promises';
import { createLogger } from '../../utils/logger/Logger.js';

const logger = createLogger({ name: 'ResponsePatternResolver' });

/**
 * API response pattern definition
 */
export interface ResponsePattern {
  apiId: string;
  pattern: 'wrapped' | 'direct';
  wrapperField?: string;
  description: string;
  mappingNote: string;
  example: {
    input?: Record<string, unknown>;
    output: Record<string, unknown>;
  };
}

/**
 * Response patterns configuration file structure
 */
export interface ResponsePatternsConfig {
  version?: string;
  patterns: Record<string, Omit<ResponsePattern, 'apiId'>>;
}

/**
 * Default configuration path
 */
const DEFAULT_CONFIG_PATH = 'config/response-patterns.yaml';

/**
 * ResponsePatternResolver - Resolves API response patterns
 *
 * Usage:
 * ```typescript
 * const resolver = new ResponsePatternResolver();
 * await resolver.load();
 * const pattern = resolver.resolvePattern('json_output_agent');
 * const hint = resolver.getMappingHint('json_output_agent');
 * ```
 */
export class ResponsePatternResolver {
  private patterns = new Map<string, ResponsePattern>();
  private loaded = false;
  private readonly configPath: string;

  constructor(configPath: string = DEFAULT_CONFIG_PATH) {
    this.configPath = configPath;
  }

  /**
   * Load pattern definitions from YAML file
   *
   * Uses js-yaml safeLoad for security (prevents YAML injection attacks)
   * Implements graceful degradation - errors are logged but don't throw
   */
  async load(): Promise<void> {
    if (this.loaded) {
      return;
    }

    try {
      const content = await readFile(this.configPath, 'utf-8');

      // Security: Use safeLoad with JSON_SCHEMA to prevent code execution
      // This rejects dangerous YAML tags like !!js/function
      const config = yaml.load(content, { schema: yaml.JSON_SCHEMA }) as ResponsePatternsConfig;

      // Validate configuration structure
      this.validateConfig(config);

      // Store patterns with apiId
      for (const [apiId, pattern] of Object.entries(config.patterns)) {
        this.patterns.set(apiId, { apiId, ...pattern });
      }

      logger.info(`Loaded ${this.patterns.size} response patterns`, {
        path: this.configPath,
        patternIds: Array.from(this.patterns.keys()),
      });

      this.loaded = true;
    } catch (error) {
      // Graceful degradation: log error but don't throw
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error('Failed to load response patterns', {
        path: this.configPath,
        error: errorMessage,
      });
      logger.warn('Continuing without response patterns - workflow generation may produce incorrect mapping paths');

      // Mark as loaded to prevent retry attempts
      this.loaded = true;
    }
  }

  /**
   * Validate response patterns configuration
   *
   * @throws Error if configuration is invalid
   */
  private validateConfig(config: ResponsePatternsConfig): void {
    // Check for patterns field
    if (!config.patterns || typeof config.patterns !== 'object') {
      throw new Error('Invalid response patterns config: missing or invalid patterns field');
    }

    // Warn if version is missing
    if (!config.version) {
      logger.warn('Response patterns config missing version field');
    }

    // Validate each pattern
    for (const [apiId, pattern] of Object.entries(config.patterns)) {
      // Check pattern type
      if (!pattern.pattern || !['wrapped', 'direct'].includes(pattern.pattern)) {
        throw new Error(`Invalid pattern type for ${apiId}: ${pattern.pattern}`);
      }

      // Check wrapperField for wrapped patterns
      if (pattern.pattern === 'wrapped' && !pattern.wrapperField) {
        throw new Error(`Wrapped pattern for ${apiId} missing wrapperField`);
      }

      // Check required fields
      if (!pattern.description) {
        logger.warn(`Pattern ${apiId} missing description`);
      }

      if (!pattern.mappingNote) {
        logger.warn(`Pattern ${apiId} missing mappingNote`);
      }

      if (!pattern.example?.output) {
        logger.warn(`Pattern ${apiId} missing example.output`);
      }
    }
  }

  /**
   * Resolve pattern for a capability ID
   *
   * @param capabilityId - The capability ID to resolve pattern for
   * @returns ResponsePattern if found, undefined otherwise
   */
  resolvePattern(capabilityId: string): ResponsePattern | undefined {
    const pattern = this.patterns.get(capabilityId);

    if (pattern) {
      logger.debug(`Pattern resolved for ${capabilityId}`, { pattern: pattern.pattern });
    } else {
      logger.debug(`No pattern defined for ${capabilityId}`);
    }

    return pattern;
  }

  /**
   * Get mapping hint for LLM prompt
   *
   * Returns a human-readable hint about how to correctly reference
   * the API response in workflow mappings.
   *
   * @param capabilityId - The capability ID
   * @returns Mapping hint string, or undefined if pattern not found
   */
  getMappingHint(capabilityId: string): string | undefined {
    const pattern = this.resolvePattern(capabilityId);
    if (!pattern) {
      return undefined;
    }

    if (pattern.pattern === 'wrapped' && pattern?.wrapperField) {
      return (
        `Warning: This API wraps response in "${pattern.wrapperField}" field. ` +
        `Use: steps.{step_id}.${pattern.wrapperField}.{field}`
      );
    }

    return 'Direct access: steps.{step_id}.{field}';
  }

  /**
   * Get the number of loaded patterns
   *
   * Useful for testing and monitoring
   */
  getPatternCount(): number {
    return this.patterns.size;
  }

  /**
   * Check if patterns have been loaded
   */
  isLoaded(): boolean {
    return this.loaded;
  }

  /**
   * Get all loaded patterns
   *
   * Returns a copy of the patterns array
   */
  getAllPatterns(): ResponsePattern[] {
    return Array.from(this.patterns.values());
  }
}

/**
 * Factory function to create ResponsePatternResolver
 *
 * @param configPath - Optional custom configuration path
 * @returns New ResponsePatternResolver instance
 */
export function createResponsePatternResolver(
  configPath: string = DEFAULT_CONFIG_PATH
): ResponsePatternResolver {
  return new ResponsePatternResolver(configPath);
}
