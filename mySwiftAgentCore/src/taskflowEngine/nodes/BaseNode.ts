/**
 * BaseNode - Node executor interface and base types
 *
 * Issue #363: Defines the NodeExecutor interface and registry
 * Issue #377: Added optional requiredSecrets property and getRequiredSecrets method
 */

import type { NodeType } from '../types/TaskFlowDefinition.js';

/**
 * Node configuration
 */
export interface NodeConfig {
  nodeId: string;
  type: NodeType | string;
  config: Record<string, unknown>;
}

/**
 * Node execution result
 */
export interface NodeResult {
  success: boolean;
  output: unknown;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  metadata?: Record<string, unknown>;
}

/**
 * CapabilityExecutor interface for URL resolution and execution
 * Issue #372: Defined here to avoid circular imports
 */
export interface ICapabilityExecutor {
  execute(
    capabilityId: string,
    params: Record<string, unknown>,
    context: NodeExecutionContext,
    projectId?: string
  ): Promise<NodeResult>;
}

/**
 * Execution context passed to nodes
 */
export interface NodeExecutionContext {
  workflowId: string;
  stepResults: Record<string, unknown>;
  variables: Record<string, unknown>;
  secrets: Record<string, string>;
  timeout?: number;
  /** Issue #372: CapabilityExecutor for capability_id based API execution */
  capabilityExecutor?: ICapabilityExecutor;
}

/**
 * Validation result for node config
 */
export interface NodeValidationResult {
  valid: boolean;
  errors: string[];
}

// Type aliases for backward compatibility (used locally in node implementations)
export type ExecutionContext = NodeExecutionContext;
export type ValidationResult = NodeValidationResult;

/**
 * NodeExecutor interface - Strategy pattern for node implementations
 *
 * Each node type implements this interface to provide:
 * - execute: Run the node logic
 * - validate: Validate node configuration
 * - requiredSecrets: (optional) Static list of required secrets
 * - getRequiredSecrets: (optional) Dynamic secret requirements based on config
 *
 * Issue #377: Added optional requiredSecrets and getRequiredSecrets for unified secrets injection
 */
export interface NodeExecutor {
  readonly type: NodeType | string;

  /**
   * Issue #377: Static list of secret keys required by this node type
   *
   * Used for nodes with fixed secret requirements (e.g., LlmNode always needs API keys)
   */
  readonly requiredSecrets?: readonly string[];

  /**
   * Execute the node
   *
   * @param config - Node configuration
   * @param params - Input parameters
   * @param context - Execution context
   * @returns Node result
   */
  execute(
    config: NodeConfig,
    params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult>;

  /**
   * Validate node configuration
   *
   * @param config - Node configuration to validate
   * @returns Validation result
   */
  validate(config: NodeConfig): NodeValidationResult;

  /**
   * Issue #377: Get dynamic secret requirements based on node configuration
   *
   * Used for nodes where secret requirements depend on config (e.g., ApiRestNode with auth)
   *
   * @param config - Node configuration
   * @returns Promise resolving to array of required secret keys
   */
  getRequiredSecrets?(config: NodeConfig): Promise<string[]>;
}

/**
 * NodeRegistry - Manages node executor implementations
 */
export class NodeRegistry {
  private readonly executors: Map<string, NodeExecutor>;

  constructor() {
    this.executors = new Map();
  }

  /**
   * Register a node executor
   *
   * @param type - Node type identifier
   * @param executor - The executor implementation
   */
  register(type: string, executor: NodeExecutor): void {
    this.executors.set(type, executor);
  }

  /**
   * Get a node executor by type
   *
   * @param type - Node type identifier
   * @returns The executor or undefined
   */
  get(type: string): NodeExecutor | undefined {
    return this.executors.get(type);
  }

  /**
   * Check if a type is registered
   *
   * @param type - Node type identifier
   * @returns true if registered
   */
  has(type: string): boolean {
    return this.executors.has(type);
  }

  /**
   * List all registered types
   *
   * @returns Array of type identifiers
   */
  listTypes(): string[] {
    return Array.from(this.executors.keys());
  }
}

/**
 * Factory to create node executor (placeholder for subclass creation)
 */
export function createNodeExecutor(
  _type: NodeType | string
): NodeExecutor | undefined {
  // This would be implemented by specific node types
  return undefined;
}

/**
 * Factory to create NodeRegistry
 */
export function createNodeRegistry(): NodeRegistry {
  return new NodeRegistry();
}
