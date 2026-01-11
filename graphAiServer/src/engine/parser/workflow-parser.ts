/**
 * Workflow Parser
 *
 * This module parses and validates workflow definitions.
 * Creates node instances from step definitions.
 *
 * @module engine/parser/workflow-parser
 * @see Issue #348
 */

import type { WorkflowDefinition, Step, BaseStep } from '../../types/taskflow.js';
import {
  WorkflowDefinitionSchema,
  validateWorkflowDefinition,
  zodErrorToValidationErrors,
} from '../schemas/workflow-schema.js';
import { BaseNode } from '../../nodes/base-node.js';
import { createApiRestNode } from '../../nodes/api-rest-node.js';
import { createTransformNode } from '../../nodes/transform-node.js';
import { createCodeJsNode } from '../../nodes/code-js-node.js';
import type { ApiRestStep, CodeJsStep, TransformStep } from '../../types/taskflow.js';

// ============================================================
// Types
// ============================================================

/** Parsed workflow with node instances */
export interface ParsedWorkflow {
  /** Workflow definition */
  definition: WorkflowDefinition;
  /** Node instances keyed by ID */
  nodes: Map<string, BaseNode>;
  /** Step order for execution */
  executionPlan: ExecutionStep[];
}

/** Conditional block for execution plan */
export interface ConditionalBlockDef {
  type: 'conditional';
  condition: string;
  then: Array<{ id?: string; type: string; config?: unknown; steps?: unknown[]; condition?: string; then?: unknown[]; else?: unknown[] }>;
  else?: Array<{ id?: string; type: string; config?: unknown; steps?: unknown[]; condition?: string; then?: unknown[]; else?: unknown[] }>;
}

/** Execution step (single node, parallel block, or conditional) */
export interface ExecutionStep {
  /** Step type */
  type: 'single' | 'parallel' | 'conditional';
  /** Node IDs to execute (for single and parallel) */
  nodeIds: string[];
  /** Conditional block (for conditional type) */
  block?: ConditionalBlockDef;
}

/** Parse result */
export interface ParseResult {
  success: boolean;
  workflow?: ParsedWorkflow;
  errors?: Array<{ path: string; message: string; code?: string }>;
}

// ============================================================
// Node Factory
// ============================================================

/**
 * Collect nodes from a conditional branch (recursively)
 * @param branch - Array of steps in the branch
 * @param nodes - Map to store node instances
 * @param nodeIds - Set of node IDs
 * @param nodeFactory - Function to create nodes
 */
function collectNodesFromBranch(
  branch: unknown[],
  nodes: Map<string, BaseNode>,
  nodeIds: Set<string>,
  nodeFactory: (step: BaseStep) => BaseNode
): void {
  for (const step of branch) {
    if (!step || typeof step !== 'object') continue;

    const stepObj = step as Record<string, unknown>;

    if (stepObj.type === 'parallel' && Array.isArray(stepObj.steps)) {
      // Handle parallel blocks within conditional
      for (const innerStep of stepObj.steps as unknown[]) {
        const inner = innerStep as { id?: string; type: string };
        if (inner.id && !nodeIds.has(inner.id)) {
          const node = nodeFactory(innerStep as BaseStep);
          nodes.set(inner.id, node);
          nodeIds.add(inner.id);
        }
      }
    } else if (stepObj.type === 'conditional') {
      // Handle nested conditionals
      if (Array.isArray(stepObj.then)) {
        collectNodesFromBranch(stepObj.then, nodes, nodeIds, nodeFactory);
      }
      if (Array.isArray(stepObj.else)) {
        collectNodesFromBranch(stepObj.else, nodes, nodeIds, nodeFactory);
      }
    } else if (stepObj.id && typeof stepObj.id === 'string') {
      // Single step
      if (!nodeIds.has(stepObj.id)) {
        const node = nodeFactory(step as BaseStep);
        nodes.set(stepObj.id, node);
        nodeIds.add(stepObj.id);
      }
    }
  }
}

/**
 * Create a node instance from a step definition
 * @param step - Step definition
 * @returns Node instance
 */
function createNode(step: BaseStep): BaseNode {
  switch (step.type) {
    case 'api_rest':
      return createApiRestNode(step as ApiRestStep);
    case 'transform':
      return createTransformNode(step as TransformStep);
    case 'code_js':
      return createCodeJsNode(step as CodeJsStep);
    default:
      throw new Error(`Unknown node type: ${(step as BaseStep).type}`);
  }
}

// ============================================================
// Workflow Parser
// ============================================================

/**
 * Parse a workflow definition
 * @param definition - Raw workflow definition
 * @returns Parse result
 */
export function parseWorkflow(definition: unknown): ParseResult {
  // 1. Validate with Zod schema
  const validationResult = validateWorkflowDefinition(definition);

  if (!validationResult.success) {
    return {
      success: false,
      errors: zodErrorToValidationErrors(validationResult.errors),
    };
  }

  const workflowDef = validationResult.data;

  // 2. Create node instances and execution plan
  const nodes = new Map<string, BaseNode>();
  const executionPlan: ExecutionStep[] = [];
  const nodeIds = new Set<string>();

  try {
    for (const step of workflowDef.steps) {
      if (step.type === 'parallel') {
        // Parallel block
        const parallelNodeIds: string[] = [];

        for (const innerStep of step.steps) {
          // Check for duplicate IDs
          if (nodeIds.has(innerStep.id)) {
            return {
              success: false,
              errors: [
                {
                  path: `steps.${innerStep.id}`,
                  message: `Duplicate node ID: ${innerStep.id}`,
                  code: 'DUPLICATE_ID',
                },
              ],
            };
          }

          const node = createNode(innerStep);
          nodes.set(innerStep.id, node);
          nodeIds.add(innerStep.id);
          parallelNodeIds.push(innerStep.id);
        }

        executionPlan.push({
          type: 'parallel',
          nodeIds: parallelNodeIds,
        });
      } else if (step.type === 'conditional') {
        // Conditional block
        const conditionalStep = step as unknown as {
          type: 'conditional';
          condition: string;
          then: unknown[];
          else?: unknown[];
        };

        // Collect node IDs from both branches
        collectNodesFromBranch(conditionalStep.then, nodes, nodeIds, createNode);
        if (conditionalStep.else) {
          collectNodesFromBranch(conditionalStep.else, nodes, nodeIds, createNode);
        }

        executionPlan.push({
          type: 'conditional',
          nodeIds: [], // Not used for conditional
          block: {
            type: 'conditional',
            condition: conditionalStep.condition,
            then: conditionalStep.then as ConditionalBlockDef['then'],
            else: conditionalStep.else as ConditionalBlockDef['else'],
          },
        });
      } else {
        // Single step
        const singleStep = step as { id: string; type: string };
        if (nodeIds.has(singleStep.id)) {
          return {
            success: false,
            errors: [
              {
                path: `steps.${singleStep.id}`,
                message: `Duplicate node ID: ${singleStep.id}`,
                code: 'DUPLICATE_ID',
              },
            ],
          };
        }

        const node = createNode(step as BaseStep);
        nodes.set(singleStep.id, node);
        nodeIds.add(singleStep.id);

        executionPlan.push({
          type: 'single',
          nodeIds: [singleStep.id],
        });
      }
    }

    // 3. Validate output mapping references
    const outputErrors = validateOutputReferences(workflowDef.output, nodeIds);
    if (outputErrors.length > 0) {
      return {
        success: false,
        errors: outputErrors,
      };
    }

    return {
      success: true,
      workflow: {
        definition: workflowDef as unknown as WorkflowDefinition,
        nodes,
        executionPlan,
      },
    };
  } catch (error) {
    return {
      success: false,
      errors: [
        {
          path: '',
          message: error instanceof Error ? error.message : String(error),
          code: 'PARSE_ERROR',
        },
      ],
    };
  }
}

/**
 * Validate output mapping references
 * @param output - Output mapping
 * @param nodeIds - Set of valid node IDs
 * @returns Array of validation errors
 */
function validateOutputReferences(
  output: Record<string, string>,
  nodeIds: Set<string>
): Array<{ path: string; message: string; code: string }> {
  const errors: Array<{ path: string; message: string; code: string }> = [];

  for (const [key, reference] of Object.entries(output)) {
    // Parse reference to get node ID
    const match = reference.match(/^\$\{([a-zA-Z_][a-zA-Z0-9_]*)\.output/);
    if (match) {
      const nodeId = match[1];
      if (!nodeIds.has(nodeId) && nodeId !== 'inputs') {
        errors.push({
          path: `output.${key}`,
          message: `Output references unknown node: ${nodeId}`,
          code: 'UNKNOWN_NODE_REFERENCE',
        });
      }
    }
  }

  return errors;
}

/**
 * Parse and validate workflow inputs
 * @param workflow - Parsed workflow
 * @param inputs - Raw inputs
 * @returns Validation result
 */
export function validateWorkflowInputs(
  workflow: ParsedWorkflow,
  inputs: Record<string, unknown>
): { valid: boolean; errors: Array<{ path: string; message: string }> } {
  const errors: Array<{ path: string; message: string }> = [];
  const inputSchema = workflow.definition.input_schema;

  // Check required fields
  for (const [field, type] of Object.entries(inputSchema)) {
    if (inputs[field] === undefined) {
      errors.push({
        path: `inputs.${field}`,
        message: `Missing required input: ${field}`,
      });
    } else {
      // Basic type check
      const value = inputs[field];
      const actualType = getBasicType(value);

      if (type !== actualType && actualType !== 'null') {
        errors.push({
          path: `inputs.${field}`,
          message: `Input '${field}' has wrong type. Expected ${type}, got ${actualType}`,
        });
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

/**
 * Get basic type of a value
 */
function getBasicType(value: unknown): string {
  if (value === null) return 'null';
  if (Array.isArray(value)) return 'array';
  return typeof value;
}

/**
 * Validate workflow definition without parsing
 * @param definition - Raw workflow definition
 * @returns Validation result
 */
export function validateWorkflowOnly(
  definition: unknown
): { valid: boolean; errors: Array<{ path: string; message: string; code?: string }> } {
  const result = WorkflowDefinitionSchema.safeParse(definition);

  if (result.success) {
    return { valid: true, errors: [] };
  }

  return {
    valid: false,
    errors: zodErrorToValidationErrors(result.error),
  };
}
