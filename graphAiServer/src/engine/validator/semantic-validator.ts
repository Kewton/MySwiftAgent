/**
 * Semantic Validator for TaskFlow Engine
 *
 * Performs Level 2 validation - checks semantic correctness:
 * - Variable reference integrity
 * - Step ID uniqueness
 * - Output mapping validity
 * - Circular reference detection (future)
 *
 * @module engine/validator/semantic-validator
 * @see Issue #348
 */

import type {
  ValidationResult,
  ValidationIssue,
  ValidatorLayer,
} from './types.js';

// ============================================================
// Types
// ============================================================

/**
 * Variable reference with location info
 */
interface VariableReference {
  /** Variable path (e.g., "step1.output.result") */
  path: string;
  /** Location in the workflow (JSON path) */
  location: string;
}

// ============================================================
// Semantic Validator
// ============================================================

/**
 * Validates semantic correctness of workflow definitions.
 *
 * Checks include:
 * - Variable references point to defined steps
 * - No duplicate step IDs
 * - Output mapping references valid steps
 */
export class SemanticValidator implements ValidatorLayer {
  /**
   * Validate a workflow definition
   * @param definition - Workflow definition object
   * @returns Validation result
   */
  validate(definition: unknown): ValidationResult {
    const issues: ValidationIssue[] = [];

    // Type guard
    if (!definition || typeof definition !== 'object') {
      issues.push({
        severity: 'error',
        code: 'INVALID_DEFINITION',
        message: 'Definition must be an object',
      });
      return this.buildResult(issues);
    }

    const def = definition as Record<string, unknown>;

    // 1. Check variable references
    issues.push(...this.checkVariableReferences(def));

    // 2. Check duplicate step IDs
    issues.push(...this.checkDuplicateIds(def));

    // 3. Check output mapping
    issues.push(...this.checkOutputMapping(def));

    // 4. Check circular references (basic)
    issues.push(...this.checkCircularReferences(def));

    return this.buildResult(issues);
  }

  /**
   * Check that all variable references point to defined steps
   */
  private checkVariableReferences(definition: Record<string, unknown>): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const stepIds = new Set<string>();

    // Collect all step IDs
    const steps = definition.steps as unknown[] | undefined;
    if (steps) {
      this.collectStepIds(steps, stepIds);
    }

    // Find all variable references and validate them
    const refs = this.findVariableReferences(definition);

    for (const ref of refs) {
      const segments = ref.path.split('.');
      const source = segments[0];

      // Skip special sources
      if (source === 'inputs' || source === 'env' || source === 'secrets') {
        continue;
      }

      // Check if source step exists
      if (!stepIds.has(source)) {
        const availableSteps = Array.from(stepIds);
        issues.push({
          severity: 'error',
          code: 'UNDEFINED_STEP_REFERENCE',
          message: `Reference to undefined step: ${source}`,
          path: ref.location,
          suggestion: `Available steps: ${availableSteps.join(', ') || 'none'}`,
          agentFeedback: {
            targetPath: ref.location,
            category: 'reference',
            currentValue: source,
            allowedValues: availableSteps,
            expectedFormat: '${step_id.output.field}',
            fixExample:
              availableSteps.length > 0
                ? `"\${${availableSteps[0]}.output.result}"`
                : undefined,
          },
        });
      }
    }

    return issues;
  }

  /**
   * Check for duplicate step IDs
   */
  private checkDuplicateIds(definition: Record<string, unknown>): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const seenIds = new Map<string, number>();

    const steps = definition.steps as unknown[] | undefined;
    if (steps) {
      this.walkSteps(steps, (step, index, path) => {
        const stepObj = step as Record<string, unknown>;
        const id = stepObj.id as string | undefined;

        if (id) {
          if (seenIds.has(id)) {
            issues.push({
              severity: 'error',
              code: 'DUPLICATE_STEP_ID',
              message: `Duplicate step ID: ${id}`,
              path: path,
              suggestion: `Rename one of the steps with ID "${id}"`,
            });
          } else {
            seenIds.set(id, index);
          }
        }
      });
    }

    return issues;
  }

  /**
   * Check output mapping references
   */
  private checkOutputMapping(definition: Record<string, unknown>): ValidationIssue[] {
    const issues: ValidationIssue[] = [];
    const stepIds = new Set<string>();

    // Collect step IDs
    const steps = definition.steps as unknown[] | undefined;
    if (steps) {
      this.collectStepIds(steps, stepIds);
    }

    // Check output mapping
    const output = definition.output as Record<string, string> | undefined;
    if (output) {
      for (const [key, value] of Object.entries(output)) {
        if (typeof value !== 'string') continue;

        // Extract step reference
        const match = value.match(/\$\{([^.}]+)/);
        if (match) {
          const stepId = match[1];

          // Skip inputs reference
          if (stepId === 'inputs') continue;

          if (!stepIds.has(stepId)) {
            issues.push({
              severity: 'error',
              code: 'INVALID_OUTPUT_REFERENCE',
              message: `Output "${key}" references undefined step: ${stepId}`,
              path: `output.${key}`,
              suggestion: `Use a valid step ID: ${Array.from(stepIds).join(', ') || 'none defined'}`,
            });
          }
        }
      }
    }

    return issues;
  }

  /**
   * Check for circular references (placeholder for future implementation)
   */
  private checkCircularReferences(_definition: Record<string, unknown>): ValidationIssue[] {
    // TODO: Implement circular reference detection
    // This would require building a dependency graph and checking for cycles
    return [];
  }

  /**
   * Collect all step IDs including from nested structures
   */
  private collectStepIds(steps: unknown[], ids: Set<string>): void {
    for (const step of steps) {
      if (!step || typeof step !== 'object') continue;

      const stepObj = step as Record<string, unknown>;

      // Add step ID if present
      if (stepObj.id && typeof stepObj.id === 'string') {
        ids.add(stepObj.id);
      }

      // Handle parallel blocks
      if (stepObj.type === 'parallel' && Array.isArray(stepObj.steps)) {
        this.collectStepIds(stepObj.steps, ids);
      }

      // Handle conditional blocks
      if (stepObj.type === 'conditional') {
        if (Array.isArray(stepObj.then)) {
          this.collectStepIds(stepObj.then, ids);
        }
        if (Array.isArray(stepObj.else)) {
          this.collectStepIds(stepObj.else, ids);
        }
      }
    }
  }

  /**
   * Walk all steps and invoke callback
   */
  private walkSteps(
    steps: unknown[],
    callback: (step: unknown, index: number, path: string) => void,
    basePath: string = 'steps'
  ): void {
    steps.forEach((step, index) => {
      const currentPath = `${basePath}[${index}]`;
      callback(step, index, currentPath);

      if (!step || typeof step !== 'object') return;

      const stepObj = step as Record<string, unknown>;

      // Handle parallel blocks
      if (stepObj.type === 'parallel' && Array.isArray(stepObj.steps)) {
        this.walkSteps(stepObj.steps, callback, `${currentPath}.steps`);
      }

      // Handle conditional blocks
      if (stepObj.type === 'conditional') {
        if (Array.isArray(stepObj.then)) {
          this.walkSteps(stepObj.then, callback, `${currentPath}.then`);
        }
        if (Array.isArray(stepObj.else)) {
          this.walkSteps(stepObj.else, callback, `${currentPath}.else`);
        }
      }
    });
  }

  /**
   * Find all variable references in an object
   */
  private findVariableReferences(
    obj: unknown,
    path: string = ''
  ): VariableReference[] {
    const refs: VariableReference[] = [];

    if (typeof obj === 'string') {
      // Find all ${...} references in the string
      const matches = obj.matchAll(/\$\{([^}]+)\}/g);
      for (const match of matches) {
        refs.push({
          path: match[1],
          location: path,
        });
      }
    } else if (Array.isArray(obj)) {
      obj.forEach((item, i) => {
        refs.push(
          ...this.findVariableReferences(item, path ? `${path}[${i}]` : `[${i}]`)
        );
      });
    } else if (obj && typeof obj === 'object') {
      for (const [key, value] of Object.entries(obj)) {
        refs.push(
          ...this.findVariableReferences(value, path ? `${path}.${key}` : key)
        );
      }
    }

    return refs;
  }

  /**
   * Build validation result from issues
   */
  private buildResult(issues: ValidationIssue[]): ValidationResult {
    const errors = issues.filter((i) => i.severity === 'error').length;
    const warnings = issues.filter((i) => i.severity === 'warning').length;
    const infos = issues.filter((i) => i.severity === 'info').length;

    return {
      valid: errors === 0,
      issues,
      summary: { errors, warnings, infos },
    };
  }
}
