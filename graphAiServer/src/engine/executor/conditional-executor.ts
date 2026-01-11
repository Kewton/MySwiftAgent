/**
 * Conditional Executor for TaskFlow Engine
 *
 * Executes conditional blocks (if/else branching) in workflows.
 * Supports nested conditionals with depth limiting for security.
 *
 * Security Features:
 * - MAX_NESTING_DEPTH = 10 to prevent stack overflow
 * - Secure condition evaluation via condition-evaluator
 *
 * @module engine/executor/conditional-executor
 * @see Issue #348
 */

import type { NodeLog } from '../../types/taskflow.js';
import type { ContextManager } from '../context/context-manager.js';
import type { BaseNode } from '../../nodes/base-node.js';
import { evaluateCondition } from './condition-evaluator.js';
import { executeSequential } from './sequential-executor.js';
import { executeParallel } from './parallel-executor.js';

// ============================================================
// Constants
// ============================================================

/**
 * Maximum nesting depth for conditional blocks.
 * Prevents stack overflow from deeply nested or recursive conditions.
 */
export const MAX_NESTING_DEPTH = 10;

// ============================================================
// Types
// ============================================================

/**
 * Single step in a conditional branch
 */
export interface ConditionalStep {
  id?: string;
  type: string;
  config?: unknown;
  steps?: ConditionalStep[]; // For parallel blocks
  condition?: string; // For nested conditionals
  then?: ConditionalStep[];
  else?: ConditionalStep[];
}

/**
 * Conditional block definition
 */
export interface ConditionalBlock {
  type: 'conditional';
  condition: string;
  then: ConditionalStep[];
  else?: ConditionalStep[];
}

/**
 * Conditional execution result
 */
export interface ConditionalExecutionResult {
  /** All execution logs */
  logs: NodeLog[];
  /** Whether all nodes succeeded */
  allSucceeded: boolean;
  /** IDs of failed nodes */
  failedNodeIds: string[];
  /** Result of condition evaluation */
  conditionResult: boolean;
  /** Which branch was executed */
  branchTaken: 'then' | 'else' | 'none';
}

// ============================================================
// Conditional Executor
// ============================================================

/**
 * Execute a conditional block.
 *
 * Evaluates the condition and executes the appropriate branch.
 * Supports nested conditionals and parallel blocks within branches.
 *
 * @param block - Conditional block definition
 * @param nodes - Map of node instances
 * @param context - Execution context
 * @param currentDepth - Current nesting depth (for recursion protection)
 * @returns Execution result
 *
 * @example
 * ```typescript
 * const block: ConditionalBlock = {
 *   type: 'conditional',
 *   condition: "${check.output.status} == 'active'",
 *   then: [{ id: 'process_active', type: 'transform', config: {...} }],
 *   else: [{ id: 'process_inactive', type: 'transform', config: {...} }],
 * };
 *
 * const result = await executeConditional(block, nodes, context);
 * console.log(result.branchTaken); // 'then' or 'else'
 * ```
 */
export async function executeConditional(
  block: ConditionalBlock,
  nodes: Map<string, BaseNode>,
  context: ContextManager,
  currentDepth: number = 0
): Promise<ConditionalExecutionResult> {
  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];

  // Check nesting depth limit
  if (currentDepth > MAX_NESTING_DEPTH) {
    console.error(
      `[ConditionalExecutor] Maximum nesting depth (${MAX_NESTING_DEPTH}) exceeded`
    );
    return {
      logs,
      allSucceeded: false,
      failedNodeIds: ['__conditional__'],
      conditionResult: false,
      branchTaken: 'none',
    };
  }

  // Evaluate condition
  const evaluation = evaluateCondition(block.condition, context);

  console.log(`[ConditionalExecutor] Condition: ${block.condition}`);
  console.log(`[ConditionalExecutor] Evaluated: ${evaluation.evaluatedCondition}`);
  console.log(`[ConditionalExecutor] Result: ${evaluation.result}`);

  if (evaluation.error) {
    console.warn(`[ConditionalExecutor] Evaluation error: ${evaluation.error}`);
  }

  // Determine which branch to execute
  const stepsToExecute = evaluation.result
    ? block.then
    : block.else || [];

  const branchTaken: 'then' | 'else' | 'none' = evaluation.result
    ? 'then'
    : block.else && block.else.length > 0
      ? 'else'
      : 'none';

  // Execute the selected branch
  if (stepsToExecute.length === 0) {
    return {
      logs,
      allSucceeded: true,
      failedNodeIds: [],
      conditionResult: evaluation.result,
      branchTaken,
    };
  }

  // Execute each step in the branch
  for (const step of stepsToExecute) {
    const stepResult = await executeStep(step, nodes, context, currentDepth);
    logs.push(...stepResult.logs);

    if (!stepResult.allSucceeded) {
      failedNodeIds.push(...stepResult.failedNodeIds);
    }
  }

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
    conditionResult: evaluation.result,
    branchTaken,
  };
}

/**
 * Execute a single step within a branch.
 *
 * Handles different step types:
 * - Single step: executes via sequential executor
 * - Parallel block: executes via parallel executor
 * - Conditional block: recurses with depth check
 *
 * @param step - Step definition
 * @param nodes - Map of node instances
 * @param context - Execution context
 * @param currentDepth - Current nesting depth
 * @returns Execution result
 */
async function executeStep(
  step: ConditionalStep,
  nodes: Map<string, BaseNode>,
  context: ContextManager,
  currentDepth: number
): Promise<{ logs: NodeLog[]; allSucceeded: boolean; failedNodeIds: string[] }> {
  const logs: NodeLog[] = [];
  const failedNodeIds: string[] = [];

  if (step.type === 'parallel' && step.steps) {
    // Execute parallel block
    const nodeIds = step.steps
      .map((s) => s.id)
      .filter((id): id is string => id !== undefined);

    const result = await executeParallel(nodeIds, nodes, context);
    logs.push(...result.logs);

    if (!result.allSucceeded) {
      failedNodeIds.push(...result.failedNodeIds);
    }
  } else if (step.type === 'conditional' && step.condition && step.then) {
    // Execute nested conditional (increment depth)
    const nestedBlock: ConditionalBlock = {
      type: 'conditional',
      condition: step.condition,
      then: step.then,
      else: step.else,
    };

    const result = await executeConditional(
      nestedBlock,
      nodes,
      context,
      currentDepth + 1
    );
    logs.push(...result.logs);

    if (!result.allSucceeded) {
      failedNodeIds.push(...result.failedNodeIds);
    }
  } else if (step.id) {
    // Execute single step
    const result = await executeSequential([step.id], nodes, context);
    logs.push(...result.logs);

    if (!result.allSucceeded) {
      failedNodeIds.push(...result.failedNodeIds);
    }
  }

  return {
    logs,
    allSucceeded: failedNodeIds.length === 0,
    failedNodeIds,
  };
}
