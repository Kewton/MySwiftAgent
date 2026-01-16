/**
 * ParallelNode - Parallel execution coordinator
 *
 * Issue #363: Coordinates parallel step execution
 */

import type {
  NodeExecutor,
  NodeConfig,
  NodeResult,
  NodeExecutionContext,
  NodeValidationResult,
} from './BaseNode.js';

/**
 * ParallelConfig type
 */
interface ParallelConfig {
  steps?: string[];
  maxConcurrency?: number;
  failFast?: boolean;
}

/**
 * ParallelNodeExecutor - Coordinates parallel steps
 *
 * Note: This executor doesn't execute steps itself, but marks
 * steps for parallel execution by the WorkflowExecutor.
 */
export class ParallelNodeExecutor implements NodeExecutor {
  readonly type = 'parallel' as const;

  /**
   * Execute parallel coordination
   *
   * Returns step configuration for parallel execution.
   * Actual execution is handled by WorkflowExecutor.
   */
  async execute(
    config: NodeConfig,
    _params: Record<string, unknown>,
    context: NodeExecutionContext
  ): Promise<NodeResult> {
    try {
      const { steps, maxConcurrency, failFast } = config.config as ParallelConfig;

      if (!steps || !Array.isArray(steps)) {
        return {
          success: false,
          output: null,
          error: {
            code: 'PARALLEL_ERROR',
            message: 'steps array is required',
          },
        };
      }

      // Return metadata for parallel execution coordination
      return {
        success: true,
        output: {
          type: 'parallel_execution',
          steps,
          maxConcurrency,
          failFast,
          status: 'pending',
          workflowId: context.workflowId,
        },
        metadata: {
          stepIds: steps,
        },
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      return {
        success: false,
        output: null,
        error: {
          code: 'PARALLEL_ERROR',
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
    const { steps, maxConcurrency } = config.config as ParallelConfig;

    if (!steps) {
      errors.push('steps array is required');
    } else if (!Array.isArray(steps)) {
      errors.push('steps must be an array');
    } else if (steps.length === 0) {
      errors.push('steps array must not be empty');
    }

    if (maxConcurrency !== undefined && (typeof maxConcurrency !== 'number' || maxConcurrency < 1)) {
      errors.push('maxConcurrency must be a positive integer');
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get steps to execute in parallel
   */
  getParallelSteps(config: NodeConfig): string[] {
    const { steps } = config.config as ParallelConfig;
    return steps || [];
  }
}

/**
 * Factory function
 */
export function createParallelNodeExecutor(): ParallelNodeExecutor {
  return new ParallelNodeExecutor();
}
