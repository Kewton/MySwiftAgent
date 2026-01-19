/**
 * CircularReferenceValidator - Detects circular references in workflows
 *
 * Issue #381: Circular reference detection using DFS algorithm
 *
 * Features:
 * - DFS-based cycle detection
 * - Configurable depth limit
 * - Detailed circular path reporting
 * - Suggestions for breaking cycles
 */

import type { TaskFlowDefinition, TaskFlowStep } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import type { ValidationResult, ValidationWarning } from '../../types/generator.js';
import type {
  EnhancedValidationContext,
  ComponentValidationError,
  ComponentValidator,
} from '../../types/validation.js';
import { RegexPatternCache } from '../utils/RegexPatternCache.js';
import { SuggestionHelper } from '../utils/SuggestionHelper.js';

/**
 * CircularReferenceValidator - Detects circular dependencies
 */
export class CircularReferenceValidator implements ComponentValidator {
  readonly name = 'CircularReferenceValidator';
  private readonly DEFAULT_MAX_DEPTH = 10;

  /**
   * Validate workflow for circular references
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: EnhancedValidationContext
  ): Promise<ValidationResult> {
    // Check if circular reference check is enabled
    if (context.additionalContext?.enableCircularReferenceCheck === false) {
      return { isValid: true, errors: [], warnings: [] };
    }

    const errors: ComponentValidationError[] = [];
    const warnings: ValidationWarning[] = [];
    const maxDepth =
      context.additionalContext?.maxCircularDepth ?? this.DEFAULT_MAX_DEPTH;

    // Build dependency graph
    const dependencyGraph = this.buildDependencyGraph(workflow);

    // Track which cycles we've already reported to avoid duplicates
    const reportedCycles = new Set<string>();

    // Check each step for circular references
    for (const stepId of dependencyGraph.keys()) {
      const circularPath = this.detectCircularReference(
        stepId,
        dependencyGraph,
        maxDepth
      );

      if (circularPath) {
        // Create a normalized key for the cycle to avoid duplicates
        const cycleKey = this.normalizeCycleKey(circularPath);
        if (!reportedCycles.has(cycleKey)) {
          reportedCycles.add(cycleKey);
          errors.push(this.createCircularReferenceError(stepId, circularPath));
        }
      }
    }

    return {
      isValid: errors.length === 0,
      errors: errors as any[],
      warnings,
    };
  }

  /**
   * Build dependency graph from workflow
   * Returns a map of step ID to set of step IDs it depends on
   */
  private buildDependencyGraph(
    workflow: TaskFlowDefinition
  ): Map<string, Set<string>> {
    const graph = new Map<string, Set<string>>();
    const regexCache = RegexPatternCache.getInstance();
    const stepRefPattern = regexCache.getPattern('stepReference')!;

    // Initialize all steps in the graph
    for (const step of workflow.steps) {
      graph.set(step.id, new Set<string>());
    }

    // Find dependencies for each step
    for (const step of workflow.steps) {
      const dependencies = this.extractDependencies(step, stepRefPattern);
      graph.set(step.id, dependencies);
    }

    return graph;
  }

  /**
   * Extract step dependencies from a step's config and params
   */
  private extractDependencies(
    step: TaskFlowStep,
    stepRefPattern: RegExp
  ): Set<string> {
    const dependencies = new Set<string>();
    const stepStr = JSON.stringify(step);

    let match;
    while ((match = stepRefPattern.exec(stepStr)) !== null) {
      const referencedStepId = match[1];
      if (referencedStepId) {
        // Add dependency (including self-references)
        dependencies.add(referencedStepId);
      }
    }

    return dependencies;
  }

  /**
   * Detect circular reference using DFS
   * Returns the circular path if found, null otherwise
   */
  private detectCircularReference(
    startStepId: string,
    graph: Map<string, Set<string>>,
    maxDepth: number
  ): string[] | null {
    const visited = new Set<string>();
    const recursionStack = new Set<string>();
    const path: string[] = [];

    const dfs = (stepId: string, depth: number): string[] | null => {
      // Check depth limit
      if (depth > maxDepth) {
        return null;
      }

      // Check for cycle - if we encounter a node already in the recursion stack
      if (recursionStack.has(stepId)) {
        // Found a cycle - return the path from the cycle start to now
        const cycleStartIndex = path.indexOf(stepId);
        if (cycleStartIndex !== -1) {
          return [...path.slice(cycleStartIndex), stepId];
        }
        return [stepId, stepId]; // Self-loop case
      }

      // Skip if already fully visited (no cycle through this node)
      if (visited.has(stepId)) {
        return null;
      }

      // Mark as being visited
      recursionStack.add(stepId);
      path.push(stepId);

      // Get dependencies
      const dependencies = graph.get(stepId);
      if (dependencies) {
        for (const dep of dependencies) {
          // Check if the dependency exists in the graph
          if (!graph.has(dep)) {
            continue;
          }

          const cycle = dfs(dep, depth + 1);
          if (cycle) {
            return cycle;
          }
        }
      }

      // Backtrack
      recursionStack.delete(stepId);
      path.pop();
      visited.add(stepId);

      return null;
    };

    return dfs(startStepId, 0);
  }

  /**
   * Normalize cycle key for deduplication
   * Rotates the cycle to start with the smallest step ID
   */
  private normalizeCycleKey(path: string[]): string {
    if (path.length <= 1) {
      return path.join('->');
    }

    // Remove the last element (duplicate of first in cycle)
    const cycle = path.slice(0, -1);

    // Find the index of the smallest element
    let minIndex = 0;
    for (let i = 1; i < cycle.length; i++) {
      const current = cycle[i];
      const min = cycle[minIndex];
      if (current !== undefined && min !== undefined && current < min) {
        minIndex = i;
      }
    }

    // Rotate to start with smallest
    const normalized = [...cycle.slice(minIndex), ...cycle.slice(0, minIndex)];
    return normalized.join('->');
  }

  /**
   * Create circular reference error with suggestions
   */
  private createCircularReferenceError(
    stepId: string,
    circularPath: string[]
  ): ComponentValidationError {
    const pathStr = circularPath.join(' -> ');
    const suggestion = SuggestionHelper.createCircularReferenceSuggestion(circularPath);

    return {
      code: 'CIRCULAR_REFERENCE_DETECTED',
      message: `Circular reference detected: ${pathStr}`,
      path: `steps.${stepId}`,
      stepId,
      field: 'dependencies',
      errorCode: 'CIRCULAR_REFERENCE_DETECTED',
      suggestion,
      context: {
        sourceStep: stepId,
        circularPath,
      },
    };
  }
}
