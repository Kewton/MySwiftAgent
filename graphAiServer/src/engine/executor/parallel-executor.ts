/**
 * Parallel Executor
 *
 * Executes multiple nodes in parallel using Promise.allSettled.
 * Continues execution even if some nodes fail.
 *
 * @module engine/executor/parallel-executor
 * @see Issue #348
 */

import type { NodeLog, NodeResult } from '../../types/taskflow.js';
import { BaseNode } from '../../nodes/base-node.js';
import { ContextManager } from '../context/context-manager.js';

// ============================================================
// Types
// ============================================================

/** Parallel execution result */
export interface ParallelExecutionResult {
  /** All execution logs */
  logs: NodeLog[];
  /** Whether all nodes succeeded */
  allSucceeded: boolean;
  /** IDs of failed nodes */
  failedNodeIds: string[];
  /** Individual node results */
  results: Map<string, NodeResult>;
}

// ============================================================
// Parallel Executor
// ============================================================

/**
 * Execute nodes in parallel
 * Uses Promise.allSettled to ensure all nodes complete even if some fail.
 *
 * @param nodeIds - Array of node IDs to execute in parallel
 * @param nodes - Map of node instances
 * @param context - Execution context
 * @returns Execution result
 */
export async function executeParallel(
  nodeIds: string[],
  nodes: Map<string, BaseNode>,
  context: ContextManager
): Promise<ParallelExecutionResult> {
  console.log(`[ParallelExecutor] Starting parallel execution of ${nodeIds.length} nodes`);

  // Create execution promises
  const executions = nodeIds.map(async (nodeId) => {
    const node = nodes.get(nodeId);

    if (!node) {
      console.error(`[ParallelExecutor] Node not found: ${nodeId}`);
      return {
        nodeId,
        result: null as NodeResult | null,
        error: new Error(`Node not found: ${nodeId}`),
      };
    }

    try {
      console.log(`[ParallelExecutor] Executing node: ${nodeId}`);
      const result = await node.execute(context);
      return { nodeId, result, error: null };
    } catch (error) {
      console.error(`[ParallelExecutor] Error in node ${nodeId}:`, error);
      return { nodeId, result: null, error };
    }
  });

  // Execute all in parallel
  const settled = await Promise.allSettled(executions);

  // Collect results
  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];
  const results = new Map<string, NodeResult>();

  for (let i = 0; i < settled.length; i++) {
    const nodeId = nodeIds[i];
    const settlement = settled[i];

    if (settlement.status === 'fulfilled') {
      const { result, error } = settlement.value;

      if (result) {
        logs.push(result.log);
        results.set(nodeId, result);

        if (!result.success) {
          failedNodeIds.push(nodeId);
        }
      } else if (error) {
        failedNodeIds.push(nodeId);
        const errorLog: NodeLog = {
          nodeId,
          state: 'failed',
          startTime: Date.now(),
          endTime: Date.now(),
          retryCount: 0,
          error: {
            message: error instanceof Error ? error.message : String(error),
            stack: error instanceof Error ? error.stack : undefined,
          },
        };
        logs.push(errorLog);
      }
    } else {
      // Promise was rejected (shouldn't happen with our try/catch, but handle it)
      failedNodeIds.push(nodeId);
      const reason = settlement.reason;
      const errorLog: NodeLog = {
        nodeId,
        state: 'failed',
        startTime: Date.now(),
        endTime: Date.now(),
        retryCount: 0,
        error: {
          message: reason instanceof Error ? reason.message : String(reason),
          stack: reason instanceof Error ? reason.stack : undefined,
        },
      };
      logs.push(errorLog);
    }
  }

  console.log(
    `[ParallelExecutor] Completed parallel execution. Success: ${nodeIds.length - failedNodeIds.length}, Failed: ${failedNodeIds.length}`
  );

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
    results,
  };
}

/**
 * Execute nodes in parallel with concurrency limit
 * @param nodeIds - Array of node IDs to execute
 * @param nodes - Map of node instances
 * @param context - Execution context
 * @param concurrency - Maximum concurrent executions
 * @returns Execution result
 */
export async function executeParallelWithLimit(
  nodeIds: string[],
  nodes: Map<string, BaseNode>,
  context: ContextManager,
  concurrency: number = 10
): Promise<ParallelExecutionResult> {
  if (nodeIds.length <= concurrency) {
    // No need for limiting
    return executeParallel(nodeIds, nodes, context);
  }

  console.log(
    `[ParallelExecutor] Executing ${nodeIds.length} nodes with concurrency limit of ${concurrency}`
  );

  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];
  const results = new Map<string, NodeResult>();

  // Process in batches
  for (let i = 0; i < nodeIds.length; i += concurrency) {
    const batch = nodeIds.slice(i, i + concurrency);
    console.log(`[ParallelExecutor] Processing batch ${Math.floor(i / concurrency) + 1}`);

    const batchResult = await executeParallel(batch, nodes, context);

    logs.push(...batchResult.logs);
    failedNodeIds.push(...batchResult.failedNodeIds);

    for (const [id, result] of batchResult.results) {
      results.set(id, result);
    }
  }

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
    results,
  };
}
