/**
 * Sequential Executor
 *
 * Executes nodes in sequence, one at a time.
 * Each node's output becomes available to subsequent nodes.
 *
 * @module engine/executor/sequential-executor
 * @see Issue #348
 */

import type { NodeLog, NodeResult } from '../../types/taskflow.js';
import { BaseNode } from '../../nodes/base-node.js';
import { ContextManager } from '../context/context-manager.js';

// ============================================================
// Types
// ============================================================

/** Sequential execution result */
export interface SequentialExecutionResult {
  /** All execution logs */
  logs: NodeLog[];
  /** Whether all nodes succeeded */
  allSucceeded: boolean;
  /** IDs of failed nodes */
  failedNodeIds: string[];
}

// ============================================================
// Sequential Executor
// ============================================================

/**
 * Execute nodes sequentially
 * @param nodeIds - Array of node IDs to execute in order
 * @param nodes - Map of node instances
 * @param context - Execution context
 * @returns Execution result
 */
export async function executeSequential(
  nodeIds: string[],
  nodes: Map<string, BaseNode>,
  context: ContextManager
): Promise<SequentialExecutionResult> {
  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];

  for (const nodeId of nodeIds) {
    const node = nodes.get(nodeId);

    if (!node) {
      console.error(`[SequentialExecutor] Node not found: ${nodeId}`);
      continue;
    }

    console.log(`[SequentialExecutor] Executing node: ${nodeId}`);

    try {
      const result = await node.execute(context);
      logs.push(result.log);

      if (!result.success) {
        failedNodeIds.push(nodeId);
        console.warn(`[SequentialExecutor] Node ${nodeId} failed:`, result.error?.message);
      } else {
        console.log(`[SequentialExecutor] Node ${nodeId} completed successfully`);
      }
    } catch (error) {
      console.error(`[SequentialExecutor] Unexpected error in node ${nodeId}:`, error);
      failedNodeIds.push(nodeId);

      // Create a log entry for the unexpected error
      logs.push({
        nodeId,
        state: 'failed',
        startTime: Date.now(),
        endTime: Date.now(),
        retryCount: 0,
        error: {
          message: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        },
      });
    }
  }

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
  };
}

/**
 * Execute a single node
 * @param node - Node instance
 * @param context - Execution context
 * @returns Node execution result
 */
export async function executeSingleNode(
  node: BaseNode,
  context: ContextManager
): Promise<NodeResult> {
  console.log(`[SequentialExecutor] Executing single node: ${node.id}`);

  try {
    const result = await node.execute(context);
    return result;
  } catch (error) {
    console.error(`[SequentialExecutor] Unexpected error in node ${node.id}:`, error);

    return {
      success: false,
      error: {
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
        code: 'EXECUTION_ERROR',
      },
      log: {
        nodeId: node.id,
        state: 'failed',
        startTime: Date.now(),
        endTime: Date.now(),
        retryCount: 0,
        error: {
          message: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined,
        },
      },
    };
  }
}
