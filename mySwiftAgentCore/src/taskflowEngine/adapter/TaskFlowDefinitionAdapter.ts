/**
 * TaskFlowDefinitionAdapter - Type conversion between external and internal formats
 *
 * Issue #363: Adapter for converting between graphAiServer TaskFlow format
 * and internal unified workflow format.
 */

import type {
  TaskFlowDefinition,
  TaskFlowStep,
} from '../types/TaskFlowDefinition.js';
import type {
  InternalWorkflowDefinition,
  InternalWorkflowStep,
} from '../types/InternalWorkflowDefinition.js';

/**
 * TaskFlowDefinitionAdapter - Converts between external and internal workflow formats
 *
 * Responsibilities:
 * - Convert graphAiServer format to internal format (toInternal)
 * - Convert internal format to graphAiServer format (toExternal)
 * - Extract step dependencies from parameter references
 */
export class TaskFlowDefinitionAdapter {
  /**
   * Convert graphAiServer TaskFlowDefinition to InternalWorkflowDefinition
   *
   * @param external - External TaskFlowDefinition
   * @returns Internal workflow representation
   */
  static toInternal(external: TaskFlowDefinition): InternalWorkflowDefinition {
    return {
      id: this.generateId(external.workflow_name),
      name: external.workflow_name,
      version: '1.0.0',
      steps: external.steps.map((step) => this.convertStepToInternal(step)),
      inputSchema: external.input_schema,
      outputSchema: external.output_schema,
      outputMapping: external.output,
      timeout: 300000, // Default 5 minutes
    };
  }

  /**
   * Convert InternalWorkflowDefinition to graphAiServer TaskFlowDefinition
   *
   * @param internal - Internal workflow definition
   * @returns External TaskFlowDefinition
   */
  static toExternal(internal: InternalWorkflowDefinition): TaskFlowDefinition {
    return {
      workflow_name: internal.name,
      input_schema: internal.inputSchema,
      output_schema: internal.outputSchema,
      steps: internal.steps.map((step) => this.convertStepToExternal(step)),
      output: internal.outputMapping,
    };
  }

  /**
   * Convert external step to internal step
   */
  private static convertStepToInternal(step: TaskFlowStep): InternalWorkflowStep {
    return {
      id: step.id,
      name: step.description || step.id,
      type: step.type,
      config: step.config,
      params: step.params,
      dependsOn: this.extractDependencies(step),
    };
  }

  /**
   * Convert internal step to external step
   */
  private static convertStepToExternal(step: InternalWorkflowStep): TaskFlowStep {
    return {
      id: step.id,
      type: step.type,
      description: step.name,
      config: step.config,
      params: step.params,
    };
  }

  /**
   * Extract step dependencies from params variable references
   *
   * Parses ${stepId.output} or ${stepId.output.nested} patterns
   * and extracts unique step IDs as dependencies.
   *
   * @param step - The step to extract dependencies from
   * @returns Array of step IDs that this step depends on
   */
  private static extractDependencies(step: TaskFlowStep): string[] {
    const deps: string[] = [];
    const paramStr = JSON.stringify(step.params || {});

    // Match ${stepId.output} patterns
    // Exclude 'input' as it's not a step dependency
    const regex = /\$\{(\w+)\.output/g;
    let match;

    while ((match = regex.exec(paramStr)) !== null) {
      const stepId = match[1];
      if (stepId && stepId !== 'input' && !deps.includes(stepId)) {
        deps.push(stepId);
      }
    }

    return deps;
  }

  /** Counter for unique ID generation */
  private static idCounter = 0;

  /**
   * Generate a unique workflow ID from the name
   */
  private static generateId(name: string): string {
    const normalized = name.toLowerCase().replace(/\s+/g, '_');
    const counter = ++this.idCounter;
    return `wf_${normalized}_${Date.now()}_${counter}`;
  }
}

/**
 * Factory function for creating adapter
 */
export function createTaskFlowDefinitionAdapter(): typeof TaskFlowDefinitionAdapter {
  return TaskFlowDefinitionAdapter;
}
