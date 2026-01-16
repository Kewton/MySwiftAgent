/**
 * ActionNode - Generic action executor
 *
 * Issue #363: Handles generic action steps (passthrough)
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';

/**
 * ActionNodeExecutor - Generic action step executor
 *
 * This executor handles generic 'action' type steps that don't
 * require special processing. It acts as a passthrough, returning
 * success with the input parameters as output.
 */
export class ActionNodeExecutor implements NodeExecutor {
  readonly type = 'action' as const;

  /**
   * Execute action (passthrough)
   */
  async execute(
    _config: NodeConfig,
    params: Record<string, unknown>,
    _context: NodeExecutionContext
  ): Promise<NodeResult> {
    // Generic action - return params as output
    return {
      success: true,
      output: params,
      metadata: {
        type: 'action',
        passthrough: true,
      },
    };
  }

  /**
   * Validate configuration (always valid for generic actions)
   */
  validate(_config: NodeConfig): NodeValidationResult {
    return {
      valid: true,
      errors: [],
    };
  }
}

/**
 * Factory function
 */
export function createActionNodeExecutor(): ActionNodeExecutor {
  return new ActionNodeExecutor();
}
