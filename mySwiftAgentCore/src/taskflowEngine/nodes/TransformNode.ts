/**
 * TransformNode - Data transformation executor
 *
 * Issue #363: Transforms data using templates or mappings
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';

/**
 * TransformNodeExecutor - Transforms data
 *
 * Supports:
 * - Template-based transformation (Handlebars-like)
 * - Mapping-based transformation
 * - Nested value access
 */
export class TransformNodeExecutor implements NodeExecutor {
  readonly type = 'transform' as const;

  /**
   * Execute transformation
   */
  async execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    _context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const { template, mapping } = config.config as {
        template?: string;
        mapping?: Record<string, string>;
      };

      let output: unknown;

      if (template) {
        output = this.transformWithTemplate(template, params);
      } else if (mapping) {
        output = this.transformWithMapping(mapping, params);
      } else {
        return {
          success: false,
          output: null,
          error: {
            code: 'TRANSFORM_ERROR',
            message: 'No template or mapping provided',
          },
        };
      }

      return {
        success: true,
        output,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: {
          code: 'TRANSFORM_ERROR',
          message,
        },
      };
    }
  }

  /**
   * Validate configuration
   */
  validate(config: NodeConfig): NodeValidationResult {
    const errors: string[] = [];
    const { template, mapping } = config.config as {
      template?: string;
      mapping?: Record<string, string>;
    };

    if (!template && !mapping) {
      errors.push('Either template or mapping is required');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Transform using template
   */
  private transformWithTemplate(
    template: string,
    params: Record<string, unknown>
  ): unknown {
    // Replace {{path}} patterns with values
    let result = template.replace(/\{\{([^}]+)\}\}/g, (_match, path) => {
      const value = this.getNestedValue(params, path.trim());
      if (value === undefined) {
        return '';
      }
      // For complex types, return JSON
      if (typeof value === 'object') {
        return JSON.stringify(value);
      }
      return String(value);
    });

    // Try to parse as JSON
    try {
      return JSON.parse(result);
    } catch {
      return result;
    }
  }

  /**
   * Transform using mapping
   */
  private transformWithMapping(
    mapping: Record<string, string>,
    params: Record<string, unknown>
  ): Record<string, unknown> {
    const result: Record<string, unknown> = {};

    for (const [outputKey, inputPath] of Object.entries(mapping)) {
      // Remove $ prefix if present
      const cleanPath = inputPath.startsWith('$.')
        ? inputPath.slice(2)
        : inputPath;
      result[outputKey] = this.getNestedValue(params, cleanPath);
    }

    return result;
  }

  /**
   * Get nested value from object
   */
  private getNestedValue(
    obj: Record<string, unknown>,
    path: string
  ): unknown {
    const parts = path.split('.');
    let current: unknown = obj;

    for (const part of parts) {
      if (current === null || current === undefined) {
        return undefined;
      }
      if (typeof current === 'object') {
        current = (current as Record<string, unknown>)[part];
      } else {
        return undefined;
      }
    }

    return current;
  }
}

/**
 * Factory function
 */
export function createTransformNodeExecutor(): TransformNodeExecutor {
  return new TransformNodeExecutor();
}
