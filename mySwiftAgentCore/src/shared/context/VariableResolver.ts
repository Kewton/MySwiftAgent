/**
 * VariableResolver - Variable resolution for workflow execution
 *
 * Resolves variable references in workflow configurations,
 * supporting template syntax and nested variable access.
 */

import type { ExecutionContext } from './ExecutionContext.js';

/**
 * Variable source types
 */
export type VariableSource = 'context' | 'step' | 'environment' | 'secret';

/**
 * Variable reference pattern: ${source.path}
 * Examples:
 *   ${context.variables.input_data}
 *   ${step.step_1.output.result}
 *   ${env.API_KEY}
 *   ${secret.database_password}
 */
const VARIABLE_PATTERN = /\$\{([^}]+)\}/g;

/**
 * Parsed variable reference
 */
export interface VariableReference {
  source: VariableSource;
  path: string[];
  fullMatch: string;
}

/**
 * Variable resolution result
 */
export interface ResolutionResult {
  resolved: boolean;
  value: unknown;
  error?: string;
}

/**
 * VariableResolver class - resolves variable references in values
 */
export class VariableResolver {
  private readonly secretProvider?: (key: string) => Promise<string | undefined>;

  constructor(options?: { secretProvider?: (key: string) => Promise<string | undefined> }) {
    this.secretProvider = options?.secretProvider;
  }

  /**
   * Resolve all variables in a value
   */
  async resolve(value: unknown, context: ExecutionContext): Promise<unknown> {
    if (typeof value === 'string') {
      return this.resolveString(value, context);
    }

    if (Array.isArray(value)) {
      return Promise.all(value.map((item) => this.resolve(item, context)));
    }

    if (value !== null && typeof value === 'object') {
      const resolved: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(value)) {
        resolved[key] = await this.resolve(val, context);
      }
      return resolved;
    }

    return value;
  }

  /**
   * Resolve variables in a string value
   */
  async resolveString(template: string, context: ExecutionContext): Promise<string> {
    const matches = template.matchAll(VARIABLE_PATTERN);
    let result = template;

    for (const match of matches) {
      const [fullMatch, expression] = match;
      if (!expression) continue;

      const reference = this.parseReference(expression, fullMatch);
      const resolution = await this.resolveReference(reference, context);

      if (resolution.resolved) {
        result = result.replace(
          fullMatch,
          typeof resolution.value === 'string' ? resolution.value : JSON.stringify(resolution.value)
        );
      }
    }

    return result;
  }

  /**
   * Parse a variable reference expression
   */
  parseReference(expression: string, fullMatch: string): VariableReference {
    const parts = expression.split('.');
    const sourceStr = parts[0] ?? '';
    const path = parts.slice(1);

    let source: VariableSource;
    switch (sourceStr) {
      case 'context':
        source = 'context';
        break;
      case 'step':
        source = 'step';
        break;
      case 'env':
        source = 'environment';
        break;
      case 'secret':
        source = 'secret';
        break;
      default:
        source = 'context';
        // If no recognized source, treat the whole thing as a context path
        path.unshift(sourceStr);
    }

    return { source, path, fullMatch };
  }

  /**
   * Resolve a single variable reference
   */
  async resolveReference(
    reference: VariableReference,
    context: ExecutionContext
  ): Promise<ResolutionResult> {
    try {
      switch (reference.source) {
        case 'context':
          return this.resolveContextVariable(reference.path, context);

        case 'step':
          return this.resolveStepVariable(reference.path, context);

        case 'environment':
          return this.resolveEnvironmentVariable(reference.path);

        case 'secret':
          return await this.resolveSecretVariable(reference.path);

        default:
          return {
            resolved: false,
            value: undefined,
            error: `Unknown source: ${reference.source}`,
          };
      }
    } catch (error) {
      return {
        resolved: false,
        value: undefined,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Resolve a context variable
   */
  private resolveContextVariable(path: string[], context: ExecutionContext): ResolutionResult {
    const first = path[0];
    if (!first) {
      return { resolved: false, value: undefined, error: 'Empty path' };
    }

    const rest = path.slice(1);
    let value: unknown;

    if (first === 'variables') {
      value = context.getAllVariables();
    } else if (first === 'metadata') {
      const metaKey = rest[0];
      if (!metaKey) {
        return { resolved: false, value: undefined, error: 'Missing metadata key' };
      }
      value = context.getMetadata(metaKey);
      return { resolved: value !== undefined, value };
    } else {
      value = context.getVariable(first);
      if (value === undefined) {
        return { resolved: false, value: undefined, error: `Variable not found: ${first}` };
      }
      return { resolved: true, value: this.getNestedValue(value, rest) };
    }

    return { resolved: true, value: this.getNestedValue(value, rest) };
  }

  /**
   * Resolve a step output variable
   */
  private resolveStepVariable(path: string[], context: ExecutionContext): ResolutionResult {
    if (path.length < 2) {
      return {
        resolved: false,
        value: undefined,
        error: 'Step reference requires step ID and path',
      };
    }

    const [stepId, ...outputPath] = path;
    if (!stepId) {
      return { resolved: false, value: undefined, error: 'Missing step ID' };
    }

    const stepResult = context.getStepResult(stepId);
    if (!stepResult) {
      return { resolved: false, value: undefined, error: `Step not found: ${stepId}` };
    }

    if (outputPath[0] === 'output') {
      const value = this.getNestedValue(stepResult.output, outputPath.slice(1));
      return { resolved: true, value };
    }

    return {
      resolved: false,
      value: undefined,
      error: `Invalid step path: ${outputPath.join('.')}`,
    };
  }

  /**
   * Resolve an environment variable
   */
  private resolveEnvironmentVariable(path: string[]): ResolutionResult {
    const [varName] = path;
    if (!varName) {
      return { resolved: false, value: undefined, error: 'Missing environment variable name' };
    }

    const value = process.env[varName];
    if (value === undefined) {
      return {
        resolved: false,
        value: undefined,
        error: `Environment variable not found: ${varName}`,
      };
    }

    return { resolved: true, value };
  }

  /**
   * Resolve a secret variable
   */
  private async resolveSecretVariable(path: string[]): Promise<ResolutionResult> {
    const [secretKey] = path;
    if (!secretKey) {
      return { resolved: false, value: undefined, error: 'Missing secret key' };
    }

    if (!this.secretProvider) {
      return { resolved: false, value: undefined, error: 'Secret provider not configured' };
    }

    const value = await this.secretProvider(secretKey);
    if (value === undefined) {
      return { resolved: false, value: undefined, error: `Secret not found: ${secretKey}` };
    }

    return { resolved: true, value };
  }

  /**
   * Get a nested value from an object using a path
   */
  private getNestedValue(obj: unknown, path: string[]): unknown {
    let current = obj;
    for (const key of path) {
      if (current === null || current === undefined) {
        return undefined;
      }
      if (typeof current === 'object') {
        current = (current as Record<string, unknown>)[key];
      } else {
        return undefined;
      }
    }
    return current;
  }
}

/**
 * Factory function to create VariableResolver
 */
export function createVariableResolver(options?: {
  secretProvider?: (key: string) => Promise<string | undefined>;
}): VariableResolver {
  return new VariableResolver(options);
}
