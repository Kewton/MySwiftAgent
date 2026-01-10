/**
 * Context Manager for TaskFlow Engine
 *
 * This module manages execution context including:
 * - Workflow inputs
 * - Node outputs
 * - Environment variables
 * - Secrets (via MyVault integration)
 * - Variable reference resolution
 *
 * Variable Reference Format:
 * - ${inputs.field} - Workflow input parameters
 * - ${node_id.output.field} - Previous node output
 * - ${env.VAR_NAME} - Environment variable
 * - ${secrets.KEY} - MyVault secret
 * - ${reference ?? default_value} - Default value support
 *
 * @module engine/context/context-manager
 * @see Issue #348
 */

import type {
  ExecutionContext,
  NodeError,
  ParsedReference,
  ReferenceSource,
} from '../../types/taskflow.js';
import { secretsManager } from '../../services/secretsManager.js';

// ============================================================
// Constants (Issue #349)
// ============================================================

/**
 * Maximum number of references in a coalesce chain.
 * Prevents performance degradation and potential DoS attacks.
 * @see Issue #349
 */
export const MAX_COALESCE_REFERENCES = 10;

// ============================================================
// Variable Reference Parser
// ============================================================

/**
 * Regular expression to match variable references
 * Matches: ${source.path.to.field} or ${source.path ?? default}
 */
const VARIABLE_REFERENCE_REGEX = /\$\{([^}]+)\}/g;

/**
 * Parse a variable reference string
 * @param reference - Reference string like "inputs.user_id" or "fetch_user.output.name"
 * @returns Parsed reference object or null if invalid
 */
function parseReference(reference: string): ParsedReference | null {
  // Handle default value syntax: ${ref ?? default}
  let refPart = reference;
  let defaultValue: unknown = undefined;

  if (reference.includes('??')) {
    const parts = reference.split('??').map((p) => p.trim());
    refPart = parts[0];
    const defaultStr = parts[1];

    // Parse default value
    if (defaultStr === 'null') {
      defaultValue = null;
    } else if (defaultStr === 'true') {
      defaultValue = true;
    } else if (defaultStr === 'false') {
      defaultValue = false;
    } else if (/^-?\d+(\.\d+)?$/.test(defaultStr)) {
      defaultValue = parseFloat(defaultStr);
    } else if (defaultStr.startsWith("'") && defaultStr.endsWith("'")) {
      defaultValue = defaultStr.slice(1, -1);
    } else if (defaultStr.startsWith('"') && defaultStr.endsWith('"')) {
      defaultValue = defaultStr.slice(1, -1);
    } else if (defaultStr.startsWith('{') || defaultStr.startsWith('[')) {
      try {
        defaultValue = JSON.parse(defaultStr);
      } catch {
        defaultValue = defaultStr;
      }
    } else {
      defaultValue = defaultStr;
    }
  }

  const segments = refPart.split('.');

  if (segments.length < 2) {
    return null;
  }

  const source = segments[0];

  // Determine source type
  let sourceType: ReferenceSource;
  let nodeId: string | undefined;
  let pathStart: number;

  switch (source) {
    case 'inputs':
      sourceType = 'inputs';
      pathStart = 1;
      break;
    case 'env':
      sourceType = 'env';
      pathStart = 1;
      break;
    case 'secrets':
      sourceType = 'secrets';
      pathStart = 1;
      break;
    default:
      // Assume it's a node output reference: node_id.output.field
      if (segments[1] === 'output') {
        sourceType = 'output';
        nodeId = source;
        pathStart = 2;
      } else if (segments[1] === 'error') {
        // Support for error references: node_id.error.message
        sourceType = 'output';
        nodeId = source;
        pathStart = 1; // Keep 'error' in path
      } else {
        return null;
      }
  }

  const path = segments.slice(pathStart);

  return {
    source: sourceType,
    nodeId,
    path,
    defaultValue,
    original: reference,
  };
}

/**
 * Get a nested value from an object using a path array
 * @param obj - Object to traverse
 * @param path - Array of path segments
 * @returns The value at the path or undefined
 */
function getNestedValue(obj: unknown, path: string[]): unknown {
  let current: unknown = obj;

  for (const segment of path) {
    if (current === null || current === undefined) {
      return undefined;
    }

    // Handle array index access: items[0], items[*]
    const arrayMatch = segment.match(/^(\w+)\[(\d+|\*)\]$/);
    if (arrayMatch) {
      const [, fieldName, indexOrWildcard] = arrayMatch;

      if (typeof current !== 'object') {
        return undefined;
      }

      const arrayValue = (current as Record<string, unknown>)[fieldName];

      if (!Array.isArray(arrayValue)) {
        return undefined;
      }

      if (indexOrWildcard === '*') {
        // Wildcard: extract field from all elements
        current = arrayValue;
      } else {
        const index = parseInt(indexOrWildcard, 10);
        current = arrayValue[index];
      }
    } else if (typeof current === 'object' && current !== null) {
      current = (current as Record<string, unknown>)[segment];
    } else {
      return undefined;
    }
  }

  return current;
}

// ============================================================
// Context Manager Class
// ============================================================

/**
 * Context Manager for workflow execution
 *
 * Manages all data available during workflow execution and provides
 * variable reference resolution.
 */
export class ContextManager {
  /** Workflow inputs */
  public readonly inputs: Record<string, unknown>;

  /** Node outputs keyed by node ID */
  public readonly outputs: Map<string, unknown>;

  /** Node errors keyed by node ID */
  public readonly errors: Map<string, NodeError>;

  /** Environment variables */
  public readonly env: Record<string, string>;

  /** Secrets (lazy loaded) */
  private secretsCache: Record<string, string>;

  /** Project for secrets resolution */
  private readonly project?: string;

  /** Whether secrets have been loaded */
  private secretsLoaded: boolean;

  /** Set of references currently being resolved (for circular detection - Issue #349) */
  private resolvingReferences: Set<string>;

  constructor(inputs: Record<string, unknown>, project?: string) {
    this.inputs = inputs;
    this.outputs = new Map();
    this.errors = new Map();
    this.project = project;
    this.secretsCache = {};
    this.secretsLoaded = false;
    this.resolvingReferences = new Set();

    // Capture relevant environment variables
    this.env = { ...process.env } as Record<string, string>;
  }

  /**
   * Load secrets from MyVault
   * Called lazily when secrets are first needed
   */
  async loadSecrets(): Promise<void> {
    if (this.secretsLoaded) {
      return;
    }

    try {
      this.secretsCache = await secretsManager.getSecretsForProject(this.project);
      this.secretsLoaded = true;
    } catch (error) {
      console.warn('Failed to load secrets from MyVault:', error);
      this.secretsLoaded = true; // Mark as loaded to prevent retry
    }
  }

  /**
   * Set a node's output
   * @param nodeId - Node identifier
   * @param output - Node output data
   */
  setOutput(nodeId: string, output: unknown): void {
    this.outputs.set(nodeId, output);
  }

  /**
   * Get a node's output
   * @param nodeId - Node identifier
   * @returns Node output or undefined
   */
  getOutput(nodeId: string): unknown {
    return this.outputs.get(nodeId);
  }

  /**
   * Set a node's error
   * @param nodeId - Node identifier
   * @param error - Error details
   */
  setError(nodeId: string, error: NodeError): void {
    this.errors.set(nodeId, error);
  }

  /**
   * Get a node's error
   * @param nodeId - Node identifier
   * @returns Error details or undefined
   */
  getError(nodeId: string): NodeError | undefined {
    return this.errors.get(nodeId);
  }

  /**
   * Check if a node has completed (with output or error)
   * @param nodeId - Node identifier
   * @returns true if node has result
   */
  hasResult(nodeId: string): boolean {
    return this.outputs.has(nodeId) || this.errors.has(nodeId);
  }

  /**
   * Resolve a single variable reference
   * Supports coalesce chain syntax: ${a ?? b ?? c}
   * @param reference - Reference string (without ${})
   * @returns Resolved value
   * @see Issue #349 - Coalesce chain support
   */
  async resolveReference(reference: string): Promise<unknown> {
    // Normalize reference for comparison
    const normalizedRef = reference.trim();

    // Issue #349: Handle coalesce chain syntax
    if (normalizedRef.includes('??')) {
      return this.resolveCoalesceChain(normalizedRef);
    }

    // Check for circular reference
    if (this.resolvingReferences.has(normalizedRef)) {
      throw new Error(
        `Circular reference detected: "${normalizedRef}" is already being resolved. ` +
          `Resolution stack: [${Array.from(this.resolvingReferences).join(' -> ')}]`
      );
    }

    // Add to resolution stack
    this.resolvingReferences.add(normalizedRef);

    try {
      return await this.resolveSingleReference(normalizedRef);
    } finally {
      // Remove from resolution stack (cleanup)
      this.resolvingReferences.delete(normalizedRef);
    }
  }

  /**
   * Resolve a coalesce chain (${a ?? b ?? c})
   * Returns the first non-null/undefined value
   * @param reference - Reference string containing ??
   * @returns First non-null value in chain
   * @see Issue #349
   */
  private async resolveCoalesceChain(reference: string): Promise<unknown> {
    const parts = reference.split('??').map((p) => p.trim());

    // Security check: limit chain length
    if (parts.length > MAX_COALESCE_REFERENCES) {
      throw new Error(
        `Coalesce chain exceeds maximum length (${MAX_COALESCE_REFERENCES}): ` +
          `found ${parts.length} references in "${reference.substring(0, 50)}..."`
      );
    }

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;

      // Check for circular reference within chain
      if (this.resolvingReferences.has(part)) {
        throw new Error(
          `Circular reference detected: "${part}" is already being resolved. ` +
            `Resolution stack: [${Array.from(this.resolvingReferences).join(' -> ')}]`
        );
      }

      // Add to resolution stack
      this.resolvingReferences.add(part);

      try {
        // Try to resolve as reference
        const parsed = parseReference(part);
        if (parsed) {
          const value = await this.resolveSingleReference(part);
          if (value !== undefined && value !== null) {
            return value;
          }
        } else if (isLast) {
          // Last part: treat as literal default
          return this.parseLiteralValue(part);
        }
      } catch {
        // If resolution fails, continue to next in chain
        if (isLast) {
          // Try as literal on last element
          return this.parseLiteralValue(part);
        }
      } finally {
        // Remove from resolution stack
        this.resolvingReferences.delete(part);
      }
    }

    return undefined;
  }

  /**
   * Parse a literal value from string
   * @param str - String to parse
   * @returns Parsed value
   * @see Issue #349
   */
  private parseLiteralValue(str: string): unknown {
    const trimmed = str.trim();

    if (trimmed === 'null') {
      return null;
    } else if (trimmed === 'true') {
      return true;
    } else if (trimmed === 'false') {
      return false;
    } else if (/^-?\d+(\.\d+)?$/.test(trimmed)) {
      return parseFloat(trimmed);
    } else if (trimmed.startsWith("'") && trimmed.endsWith("'")) {
      return trimmed.slice(1, -1);
    } else if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
      return trimmed.slice(1, -1);
    } else if (trimmed.startsWith('{') || trimmed.startsWith('[')) {
      try {
        return JSON.parse(trimmed);
      } catch {
        return trimmed;
      }
    }
    return trimmed;
  }

  /**
   * Resolve a single (non-coalesce) variable reference
   * @param reference - Reference string
   * @returns Resolved value
   */
  private async resolveSingleReference(reference: string): Promise<unknown> {
    const parsed = parseReference(reference);

    if (!parsed) {
      throw new Error(`Invalid variable reference: ${reference}`);
    }

    let value: unknown;

    switch (parsed.source) {
      case 'inputs':
        value = getNestedValue(this.inputs, parsed.path);
        break;

      case 'env':
        value = this.env[parsed.path[0]];
        break;

      case 'secrets':
        // Lazy load secrets
        if (!this.secretsLoaded) {
          await this.loadSecrets();
        }
        value = this.secretsCache[parsed.path[0]];

        // Try environment variable fallback
        if (value === undefined) {
          value = this.env[parsed.path[0]];
        }
        break;

      case 'output':
        if (!parsed.nodeId) {
          throw new Error(`Node ID required for output reference: ${reference}`);
        }

        // Check if it's an error reference
        if (parsed.path[0] === 'error') {
          const error = this.errors.get(parsed.nodeId);
          value = error ? getNestedValue(error, parsed.path.slice(1)) : undefined;
        } else {
          const output = this.outputs.get(parsed.nodeId);
          value = getNestedValue(output, parsed.path);
        }
        break;
    }

    // Apply default value if result is undefined/null
    if ((value === undefined || value === null) && parsed.defaultValue !== undefined) {
      return parsed.defaultValue;
    }

    return value;
  }

  /**
   * Resolve all variable references in a value
   * Handles strings, objects, and arrays recursively
   * @param value - Value to resolve
   * @returns Resolved value
   */
  async resolve(value: unknown): Promise<unknown> {
    if (typeof value === 'string') {
      return this.resolveString(value);
    }

    if (Array.isArray(value)) {
      const resolved = [];
      for (const item of value) {
        resolved.push(await this.resolve(item));
      }
      return resolved;
    }

    if (value !== null && typeof value === 'object') {
      const resolved: Record<string, unknown> = {};
      for (const [key, val] of Object.entries(value)) {
        resolved[key] = await this.resolve(val);
      }
      return resolved;
    }

    return value;
  }

  /**
   * Resolve variable references in a string
   * @param str - String potentially containing ${...} references
   * @returns Resolved string or value
   */
  private async resolveString(str: string): Promise<unknown> {
    // Check if the entire string is a single reference
    const singleRefMatch = str.match(/^\$\{([^}]+)\}$/);
    if (singleRefMatch) {
      // Return the resolved value directly (preserves type)
      return this.resolveReference(singleRefMatch[1]);
    }

    // Handle multiple references in a string
    const matches = Array.from(str.matchAll(VARIABLE_REFERENCE_REGEX));
    if (matches.length === 0) {
      return str;
    }

    let result = str;
    for (const match of matches) {
      const [fullMatch, reference] = match;
      const resolved = await this.resolveReference(reference);

      // Convert non-string values to string for embedding
      const resolvedStr =
        typeof resolved === 'string'
          ? resolved
          : resolved === undefined || resolved === null
            ? ''
            : JSON.stringify(resolved);

      result = result.replace(fullMatch, resolvedStr);
    }

    return result;
  }

  /**
   * Get the current execution context as a plain object
   * @returns Execution context snapshot
   */
  toContext(): ExecutionContext {
    return {
      inputs: this.inputs,
      env: this.env,
      secrets: this.secretsCache,
      outputs: new Map(this.outputs),
      errors: new Map(this.errors),
    };
  }

  /**
   * Build the final results object for workflow response
   * @param outputMapping - Output mapping from workflow definition
   * @returns Results object with inputs, node outputs, and _output
   */
  async buildResults(
    outputMapping: Record<string, string>
  ): Promise<Record<string, unknown>> {
    const results: Record<string, unknown> = {
      inputs: this.inputs,
    };

    // Add all node outputs
    for (const [nodeId, output] of this.outputs) {
      results[nodeId] = output;
    }

    // Add null for failed nodes
    for (const [nodeId] of this.errors) {
      if (!results[nodeId]) {
        results[nodeId] = null;
      }
    }

    // Resolve output mapping
    const _output: Record<string, unknown> = {};
    for (const [key, reference] of Object.entries(outputMapping)) {
      _output[key] = await this.resolveString(reference);
    }
    results['_output'] = _output;

    return results;
  }

  /**
   * Build the errors object for workflow response
   * @returns Errors keyed by node ID
   */
  buildErrors(): Record<string, NodeError> {
    const errors: Record<string, NodeError> = {};
    for (const [nodeId, error] of this.errors) {
      errors[nodeId] = error;
    }
    return errors;
  }
}

// ============================================================
// Exported Functions
// ============================================================

/**
 * Create a new context manager
 * @param inputs - Workflow inputs
 * @param project - Project for secrets resolution
 * @returns New ContextManager instance
 */
export function createContext(
  inputs: Record<string, unknown>,
  project?: string
): ContextManager {
  return new ContextManager(inputs, project);
}

/**
 * Parse a variable reference string
 * Exported for testing
 */
export { parseReference, getNestedValue };
