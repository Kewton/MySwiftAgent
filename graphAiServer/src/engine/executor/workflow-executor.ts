/**
 * Workflow Executor
 *
 * Main entry point for executing workflows.
 * Orchestrates sequential and parallel execution based on the execution plan.
 *
 * @module engine/executor/workflow-executor
 * @see Issue #348
 */

import type { WorkflowResult, NodeLog } from '../../types/taskflow.js';
import type { ParsedWorkflow, ExecutionStep } from '../parser/workflow-parser.js';
import { ContextManager, createContext } from '../context/context-manager.js';
import { executeSequential } from './sequential-executor.js';
import { executeParallel } from './parallel-executor.js';
import { executeConditional, type ConditionalBlock } from './conditional-executor.js';
import { schemaValidator, formatValidationErrors } from '../validator/schema-validator.js';

// ============================================================
// Types
// ============================================================

/** Workflow execution options */
export interface ExecutionOptions {
  /** Project for secrets resolution */
  project?: string;
  /** Overall execution timeout (ms) */
  timeout?: number;
  /** Maximum parallel concurrency */
  maxConcurrency?: number;
}

/** Default options */
const DEFAULT_OPTIONS: Required<ExecutionOptions> = {
  project: 'default_project',
  timeout: 300000, // 5 minutes
  maxConcurrency: 10,
};

// ============================================================
// Workflow Executor
// ============================================================

/**
 * Execute a parsed workflow
 * @param workflow - Parsed workflow with node instances
 * @param inputs - Workflow inputs
 * @param options - Execution options
 * @returns Workflow execution result
 */
export async function executeWorkflow(
  workflow: ParsedWorkflow,
  inputs: Record<string, unknown>,
  options: ExecutionOptions = {}
): Promise<WorkflowResult> {
  const opts = { ...DEFAULT_OPTIONS, ...options };
  const allLogs: NodeLog[] = [];
  let hasErrors = false;

  console.log(`[WorkflowExecutor] Starting workflow: ${workflow.definition.workflow_name}`);

  // 1. Create execution context
  const context = createContext(inputs, opts.project);

  // 2. Load secrets (lazy, will be loaded on first access)
  await context.loadSecrets();

  // 3. Validate inputs against input_schema
  const inputValidation = schemaValidator.validateInput(
    workflow.definition.input_schema,
    inputs
  );

  if (!inputValidation.valid) {
    console.warn('[WorkflowExecutor] Input validation failed:', inputValidation.errors);
    // Continue execution but log the warning
    // Some workflows might have optional fields
  }

  // 4. Execute steps according to execution plan
  try {
    for (const step of workflow.executionPlan) {
      console.log(
        `[WorkflowExecutor] Executing step: ${step.type} with nodes: ${step.nodeIds.join(', ')}`
      );

      if (step.type === 'single') {
        // Sequential execution
        const result = await executeSequential(
          step.nodeIds,
          workflow.nodes,
          context
        );

        allLogs.push(...result.logs);

        if (!result.allSucceeded) {
          hasErrors = true;
          console.warn(`[WorkflowExecutor] Sequential step had failures: ${result.failedNodeIds.join(', ')}`);
        }
      } else if (step.type === 'parallel') {
        // Parallel execution
        const result = await executeParallel(
          step.nodeIds,
          workflow.nodes,
          context
        );

        allLogs.push(...result.logs);

        if (!result.allSucceeded) {
          hasErrors = true;
          console.warn(`[WorkflowExecutor] Parallel step had failures: ${result.failedNodeIds.join(', ')}`);
        }
      } else if (step.type === 'conditional' && step.block) {
        // Conditional execution
        console.log(`[WorkflowExecutor] Executing conditional: ${step.block.condition}`);
        const result = await executeConditional(
          step.block as ConditionalBlock,
          workflow.nodes,
          context,
          0 // Initial nesting depth
        );

        allLogs.push(...result.logs);

        if (!result.allSucceeded) {
          hasErrors = true;
          console.warn(`[WorkflowExecutor] Conditional step had failures: ${result.failedNodeIds.join(', ')}`);
        }

        console.log(`[WorkflowExecutor] Conditional result: branch=${result.branchTaken}`);
      }
    }
  } catch (error) {
    console.error('[WorkflowExecutor] Unexpected error during execution:', error);
    hasErrors = true;
  }

  // 5. Build results
  const results = await context.buildResults(workflow.definition.output);
  const errors = context.buildErrors();

  // 6. Validate output
  const _output = results['_output'] as Record<string, unknown>;
  if (_output) {
    const outputValidation = schemaValidator.validateOutput(
      workflow.definition.output_schema,
      _output
    );

    if (!outputValidation.valid) {
      console.warn('[WorkflowExecutor] Output validation warnings:', outputValidation.errors);
    }
  }

  console.log(
    `[WorkflowExecutor] Workflow completed. Success: ${!hasErrors}, Errors: ${Object.keys(errors).length}`
  );

  return {
    results,
    errors,
    logs: allLogs,
  };
}

/**
 * Execute a workflow with timeout
 * @param workflow - Parsed workflow
 * @param inputs - Workflow inputs
 * @param options - Execution options
 * @returns Workflow result or timeout error
 */
export async function executeWorkflowWithTimeout(
  workflow: ParsedWorkflow,
  inputs: Record<string, unknown>,
  options: ExecutionOptions = {}
): Promise<WorkflowResult> {
  const timeout = options.timeout || DEFAULT_OPTIONS.timeout;

  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => {
      reject(new Error(`Workflow execution timed out after ${timeout}ms`));
    }, timeout);
  });

  try {
    return await Promise.race([
      executeWorkflow(workflow, inputs, options),
      timeoutPromise,
    ]);
  } catch (error) {
    // Return timeout as a workflow error
    return {
      results: { inputs },
      errors: {
        __workflow__: {
          message: error instanceof Error ? error.message : String(error),
          code: 'WORKFLOW_TIMEOUT',
        },
      },
      logs: [],
    };
  }
}

// ============================================================
// Helper Functions
// ============================================================

/**
 * Check if a workflow result has errors
 * @param result - Workflow result
 * @returns true if there are errors
 */
export function hasWorkflowErrors(result: WorkflowResult): boolean {
  return Object.keys(result.errors).length > 0;
}

/**
 * Get the final output from a workflow result
 * @param result - Workflow result
 * @returns Output object or undefined
 */
export function getWorkflowOutput(result: WorkflowResult): Record<string, unknown> | undefined {
  return result.results['_output'] as Record<string, unknown> | undefined;
}
