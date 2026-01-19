/**
 * OutputMappingValidator - Validates output mapping references against responseSchema
 *
 * Issue #375: Ensures output mappings are consistent with output_schema
 * and capability responseSchemas
 */

import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type {
  ValidationResult,
  ValidationError,
  ValidationWarning,
} from '../../types/generator.js';
import type { TaskFlowDefinition } from '../../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Extended capability type with responseSchema
 */
interface CapabilityWithResponseSchema {
  id: string;
  name: string;
  status: string;
  responseSchema?: {
    type: string;
    properties?: Record<string, { type: string; description?: string }>;
  };
}

/**
 * OutputMappingValidator - Validates output mapping consistency
 *
 * Checks:
 * - Output mapping fields match output_schema properties
 * - Required output_schema fields are present in output mapping
 * - Step references in output use valid responseSchema fields (when available)
 */
export class OutputMappingValidator implements Validator {
  readonly name = 'OutputMappingValidator';

  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    // Build capability lookup with responseSchema
    const capabilityMap = new Map<string, CapabilityWithResponseSchema>(
      context.capabilities.map((c) => [c.id, c as CapabilityWithResponseSchema])
    );

    // Build step lookup for capability_id references
    const stepCapabilityMap = new Map<string, string>();
    for (const step of workflow.steps ?? []) {
      const capabilityId = step.config['capability_id'] as string | undefined;
      if (capabilityId) {
        stepCapabilityMap.set(step.id, capabilityId);
      }
    }

    // Validate output mapping against output_schema
    this.validateOutputMapping(workflow, errors, warnings);

    // Validate step output references against responseSchema
    this.validateResponseSchemaReferences(
      workflow,
      capabilityMap,
      stepCapabilityMap,
      warnings
    );

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Validate output mapping fields against output_schema
   */
  private validateOutputMapping(
    workflow: TaskFlowDefinition,
    errors: ValidationError[],
    warnings: ValidationWarning[]
  ): void {
    const outputSchema = workflow.output_schema;
    const outputMapping = workflow.output ?? {};

    // If output_schema has no properties, allow any output mapping
    if (!outputSchema.properties) {
      return;
    }

    const schemaProperties = Object.keys(outputSchema.properties);
    const mappingFields = Object.keys(outputMapping);
    const requiredFields = outputSchema.required ?? [];

    // Check for extra fields in output mapping not in schema
    for (const field of mappingFields) {
      if (!schemaProperties.includes(field)) {
        errors.push({
          code: 'OUTPUT_MAPPING_EXTRA_FIELD',
          message: `Output mapping contains field "${field}" which is not defined in output_schema`,
          path: `output.${field}`,
        });
      }
    }

    // Check for missing required fields
    for (const requiredField of requiredFields) {
      if (!mappingFields.includes(requiredField)) {
        errors.push({
          code: 'OUTPUT_MAPPING_MISSING_REQUIRED',
          message: `Output mapping is missing required field "${requiredField}" from output_schema`,
          path: `output.${requiredField}`,
        });
      }
    }

    // Check for missing optional fields (warning)
    for (const schemaField of schemaProperties) {
      if (!requiredFields.includes(schemaField) && !mappingFields.includes(schemaField)) {
        warnings.push({
          code: 'OUTPUT_MAPPING_MISSING_OPTIONAL',
          message: `Output mapping is missing optional field "${schemaField}" from output_schema`,
        });
      }
    }
  }

  /**
   * Validate step output references against capability responseSchema
   */
  private validateResponseSchemaReferences(
    workflow: TaskFlowDefinition,
    capabilityMap: Map<string, CapabilityWithResponseSchema>,
    stepCapabilityMap: Map<string, string>,
    warnings: ValidationWarning[]
  ): void {
    const outputMapping = workflow.output ?? {};

    for (const [outputField, reference] of Object.entries(outputMapping)) {
      // Extract step ID and field from reference like $steps.step_id.field
      const match = reference.match(/\$steps\.([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)/);
      if (!match) continue;

      const stepId = match[1];
      const fieldName = match[2];
      if (!stepId || !fieldName) continue;

      // Check if step uses a capability
      const capabilityId = stepCapabilityMap.get(stepId);
      if (!capabilityId) continue;

      // Get capability with responseSchema
      const capability = capabilityMap.get(capabilityId);
      if (!capability?.responseSchema?.properties) continue;

      // Check if referenced field exists in responseSchema
      if (!Object.keys(capability.responseSchema.properties).includes(fieldName)) {
        warnings.push({
          code: 'RESPONSE_SCHEMA_FIELD_UNKNOWN',
          message: `Output "${outputField}" references field "${fieldName}" which is not defined in capability "${capability.name}" responseSchema`,
        });
      }
    }
  }
}

/**
 * Factory function
 */
export function createOutputMappingValidator(): OutputMappingValidator {
  return new OutputMappingValidator();
}
