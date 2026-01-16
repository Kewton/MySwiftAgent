/**
 * SchemaValidator - Validates workflow against TaskFlow schema
 *
 * Issue #364: Schema validation using Zod
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError } from '../../types/generator.js';
import type { TaskFlowDefinition } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import { TaskFlowDefinitionSchema } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * SchemaValidator - Validates workflow against Zod schema
 */
export class SchemaValidator implements Validator {
  readonly name = 'SchemaValidator';

  async validate(
    workflow: TaskFlowDefinition,
    _context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];

    // Validate against Zod schema
    const result = TaskFlowDefinitionSchema.safeParse(workflow);

    if (!result.success) {
      for (const issue of result.error.issues) {
        errors.push({
          code: `SCHEMA_${issue.code.toUpperCase()}`,
          message: issue.message,
          path: issue.path.join('.'),
        });
      }
    }

    // Additional validations not covered by Zod

    // Check workflow_name format (snake_case)
    if (workflow.workflow_name && !/^[a-z][a-z0-9_]*$/.test(workflow.workflow_name)) {
      errors.push({
        code: 'INVALID_WORKFLOW_NAME_FORMAT',
        message: 'workflow_name must be snake_case (lowercase letters, numbers, underscores)',
        path: 'workflow_name',
      });
    }

    // Check for empty steps
    if (workflow.steps && workflow.steps.length === 0) {
      errors.push({
        code: 'EMPTY_STEPS',
        message: 'Workflow must have at least one step',
        path: 'steps',
      });
    }

    // Check step ID format
    for (let i = 0; i < (workflow.steps?.length ?? 0); i++) {
      const step = workflow.steps[i];
      if (step && !/^[a-z][a-z0-9_]*$/.test(step.id)) {
        errors.push({
          code: 'INVALID_STEP_ID_FORMAT',
          message: `Step ID "${step.id}" must be snake_case`,
          path: `steps[${i}].id`,
        });
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  }
}
