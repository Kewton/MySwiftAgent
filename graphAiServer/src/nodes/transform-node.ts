/**
 * Transform Node Implementation
 *
 * This node performs data transformation operations:
 * - template: Handlebars template expansion
 * - concat: String/array concatenation
 * - map: Array element transformation
 * - merge: Object merging
 *
 * @module nodes/transform-node
 * @see Issue #348
 */

import Handlebars from 'handlebars';
import type { TransformConfig, TransformStep } from '../types/taskflow.js';
import { BaseNode, TemplateError, NodeExecutionError } from './base-node.js';
import { ContextManager } from '../engine/context/context-manager.js';

// ============================================================
// Handlebars Configuration
// ============================================================

// Create a sandboxed Handlebars instance
const handlebars = Handlebars.create();

// Register safe helpers
handlebars.registerHelper('eq', (a: unknown, b: unknown) => a === b);
handlebars.registerHelper('ne', (a: unknown, b: unknown) => a !== b);
handlebars.registerHelper('lt', (a: unknown, b: unknown) =>
  typeof a === 'number' && typeof b === 'number' ? a < b : false
);
handlebars.registerHelper('gt', (a: unknown, b: unknown) =>
  typeof a === 'number' && typeof b === 'number' ? a > b : false
);
handlebars.registerHelper('lte', (a: unknown, b: unknown) =>
  typeof a === 'number' && typeof b === 'number' ? a <= b : false
);
handlebars.registerHelper('gte', (a: unknown, b: unknown) =>
  typeof a === 'number' && typeof b === 'number' ? a >= b : false
);
handlebars.registerHelper('and', (a: unknown, b: unknown) => a && b);
handlebars.registerHelper('or', (a: unknown, b: unknown) => a || b);
handlebars.registerHelper('not', (a: unknown) => !a);
handlebars.registerHelper('json', (obj: unknown) => JSON.stringify(obj));
handlebars.registerHelper('length', (arr: unknown) =>
  Array.isArray(arr) ? arr.length : 0
);


// ============================================================
// Transform Node Class
// ============================================================

/**
 * Transform Node for data manipulation
 *
 * Supports multiple transformation modes:
 * - template: Handlebars template expansion
 * - concat: Concatenate strings or arrays
 * - map: Transform each element of an array
 * - merge: Deep merge objects
 */
export class TransformNode extends BaseNode<TransformConfig> {
  private compiledTemplate?: HandlebarsTemplateDelegate;

  constructor(step: TransformStep) {
    super(step);

    // Pre-compile template if provided
    if (this.config.template) {
      try {
        this.compiledTemplate = handlebars.compile(this.config.template, {
          noEscape: false, // Security: escape HTML by default
          strict: false,
          assumeObjects: false,
        });
      } catch (error) {
        throw new TemplateError(
          `Failed to compile template: ${error instanceof Error ? error.message : String(error)}`,
          this.config.template
        );
      }
    }
  }

  /**
   * Execute the transformation
   * @param params - Resolved parameters
   * @param context - Execution context
   * @returns Transformation result
   */
  protected async executeInternal(
    params: Record<string, unknown>,
    context: ContextManager
  ): Promise<unknown> {
    const mode = this.config.mode || 'template';

    switch (mode) {
      case 'template':
        return this.executeTemplate(params);

      case 'concat':
        return this.executeConcat(params);

      case 'map':
        return this.executeMap(params);

      case 'merge':
        return this.executeMerge(params);

      default:
        throw new NodeExecutionError(
          `Unknown transform mode: ${mode}`,
          'INVALID_MODE'
        );
    }
  }

  /**
   * Execute template mode: Handlebars template expansion
   * @param params - Template parameters
   * @returns Template result
   */
  private executeTemplate(params: Record<string, unknown>): { result: string } {
    if (!this.compiledTemplate) {
      throw new TemplateError('No template provided for template mode');
    }

    try {
      const result = this.compiledTemplate(params);
      return { result };
    } catch (error) {
      throw new TemplateError(
        `Template execution failed: ${error instanceof Error ? error.message : String(error)}`,
        this.config.template
      );
    }
  }

  /**
   * Execute concat mode: Concatenate strings or arrays
   * @param params - Parameters containing fields to concatenate
   * @returns Concatenation result
   */
  private executeConcat(params: Record<string, unknown>): { result: string | unknown[] } {
    const fields = this.config.fields || Object.keys(params);
    const separator = this.config.separator ?? ', ';

    const values: unknown[] = [];

    for (const field of fields) {
      const value = params[field];
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          values.push(...value);
        } else {
          values.push(value);
        }
      }
    }

    // If all values are strings, join them
    if (values.every((v) => typeof v === 'string')) {
      return { result: values.join(separator) };
    }

    // Otherwise return as array
    return { result: values };
  }

  /**
   * Execute map mode: Transform each element of an array
   * @param params - Parameters containing source array
   * @returns Mapped array
   */
  private executeMap(params: Record<string, unknown>): { result: unknown[] } {
    const sourceField = this.config.source_field || 'items';
    const source = params[sourceField];

    if (!Array.isArray(source)) {
      throw new NodeExecutionError(
        `Source field '${sourceField}' must be an array`,
        'INVALID_SOURCE'
      );
    }

    if (!this.compiledTemplate) {
      // If no template, return source as-is
      return { result: source };
    }

    try {
      const result = source.map((item, index) => {
        // Context for Handlebars template
        const context = {
          ...params,
          // Also provide without @ for backwards compatibility
          '@index': index,
          '@first': index === 0,
          '@last': index === source.length - 1,
          ...item,
        };

        // Issue #349: Pass @index, @first, @last via data option
        // This allows templates to use {{@index}}, {{@first}}, {{@last}} syntax
        const options = {
          data: {
            index: index,
            first: index === 0,
            last: index === source.length - 1,
          },
        };

        return this.compiledTemplate!(context, options);
      });

      return { result };
    } catch (error) {
      throw new TemplateError(
        `Map template execution failed: ${error instanceof Error ? error.message : String(error)}`,
        this.config.template
      );
    }
  }

  /**
   * Execute merge mode: Deep merge objects
   * @param params - Objects to merge
   * @returns Merged object
   */
  private executeMerge(params: Record<string, unknown>): { result: Record<string, unknown> } {
    const strategy = this.config.strategy || 'shallow';
    const result: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(params)) {
      // Issue #349: Auto-parse JSON strings
      const processedValue = this.parseJsonIfNeeded(value);

      if (processedValue !== null && typeof processedValue === 'object' && !Array.isArray(processedValue)) {
        if (strategy === 'deep') {
          result[key] = processedValue;
          // Deep merge into a single result object
          this.deepMerge(result, processedValue as Record<string, unknown>);
        } else {
          // Shallow: spread top-level keys
          Object.assign(result, processedValue);
        }
      } else if (processedValue !== undefined) {
        result[key] = processedValue;
      }
    }

    return { result };
  }

  /**
   * Check if a string looks like JSON (Issue #349)
   * @param str - String to check
   * @returns true if string appears to be JSON
   */
  private isJsonString(str: string): boolean {
    const trimmed = str.trim();
    return (
      (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
      (trimmed.startsWith('[') && trimmed.endsWith(']'))
    );
  }

  /**
   * Parse JSON string if needed (Issue #349)
   * @param value - Value to potentially parse
   * @returns Parsed value or original value
   */
  private parseJsonIfNeeded(value: unknown): unknown {
    if (typeof value === 'string' && this.isJsonString(value)) {
      try {
        return JSON.parse(value);
      } catch {
        // If parsing fails, return original string
        return value;
      }
    }
    return value;
  }

  /**
   * Deep merge helper
   * @param target - Target object
   * @param source - Source object
   */
  private deepMerge(
    target: Record<string, unknown>,
    source: Record<string, unknown>
  ): void {
    for (const [key, value] of Object.entries(source)) {
      if (
        value !== null &&
        typeof value === 'object' &&
        !Array.isArray(value) &&
        target[key] !== null &&
        typeof target[key] === 'object' &&
        !Array.isArray(target[key])
      ) {
        this.deepMerge(
          target[key] as Record<string, unknown>,
          value as Record<string, unknown>
        );
      } else {
        target[key] = value;
      }
    }
  }
}

// ============================================================
// Factory Function
// ============================================================

/**
 * Create a Transform node from a step definition
 * @param step - Step definition
 * @returns TransformNode instance
 */
export function createTransformNode(step: TransformStep): TransformNode {
  return new TransformNode(step);
}
