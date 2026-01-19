/**
 * ResponseSchemaValidator - Validates response schemas using ajv
 *
 * Issue #380: Response Schema validation with JSON Schema Draft-07
 * Uses ajv library with ajv-formats for format validation
 */

import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import type { Validator, ValidationContext } from '../ValidationPipeline.js';
import type { ValidationResult, ValidationError, ValidationWarning } from '../../types/generator.js';
import type { TaskFlowDefinition } from '../../../taskflowEngine/types/TaskFlowDefinition.js';
import type { ResponseSchema, ResponseSchemaProperty } from '../../../capabilities/types/catalog.js';

// Create Ajv instance constructor
const AjvClass = Ajv.default ?? Ajv;
const addFormatsFunc = addFormats.default ?? addFormats;

/**
 * Schema validation result
 */
export interface SchemaValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

/**
 * ResponseSchemaValidator - Validates JSON Schema Draft-07 schemas and data
 */
export class ResponseSchemaValidator implements Validator {
  readonly name = 'ResponseSchemaValidator';
  private ajv: InstanceType<typeof AjvClass>;

  constructor() {
    // Initialize Ajv with JSON Schema Draft-07
    this.ajv = new AjvClass({
      allErrors: true,
      verbose: true,
      strict: false,
    });

    // Add format validators (email, uri, date-time, etc.)
    addFormatsFunc(this.ajv);
  }

  /**
   * Validate workflow - Validator interface implementation
   *
   * Checks that all api_rest steps have valid responseSchema defined
   * in their associated capabilities
   */
  async validate(
    workflow: TaskFlowDefinition,
    context: ValidationContext
  ): Promise<ValidationResult> {
    const errors: ValidationError[] = [];
    const warnings: ValidationWarning[] = [];

    if (!workflow.steps) {
      return { isValid: true, errors, warnings };
    }

    for (const step of workflow.steps) {
      // Only check api_rest steps with capability_id
      if (step.type !== 'api_rest') continue;

      const capabilityId = step.config?.capability_id;
      if (!capabilityId) continue;

      // Find capability in context
      const capability = context.capabilities.find((c) => c.id === capabilityId);
      if (!capability) continue; // CapabilityValidator handles missing capabilities

      // Check for responseSchema
      const responseSchema = (capability as Record<string, unknown>).responseSchema as
        | Record<string, unknown>
        | undefined;

      if (!responseSchema) {
        warnings.push({
          code: 'MISSING_RESPONSE_SCHEMA',
          message: `Capability "${capabilityId}" does not have a responseSchema defined`,
        });
        continue;
      }

      // Validate the responseSchema itself is valid JSON Schema
      const schemaValidation = this.validateSchema(responseSchema);
      if (!schemaValidation.isValid) {
        errors.push({
          code: 'INVALID_RESPONSE_SCHEMA',
          message: `Capability "${capabilityId}" has an invalid responseSchema`,
          path: `steps.${step.id}.config.capability_id`,
        });
        errors.push(...schemaValidation.errors);
      }
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
    };
  }

  /**
   * Validate that a schema is a valid JSON Schema Draft-07
   */
  validateSchema(schema: Record<string, unknown>): SchemaValidationResult {
    const errors: ValidationError[] = [];

    try {
      // Convert YAML-style schema to JSON Schema if needed
      const jsonSchema = this.convertToJsonSchema(schema as ResponseSchema);

      // Try to compile the schema - if it compiles, it's valid
      const validate = this.ajv.compile(jsonSchema);

      // Check if there were any compilation errors
      if (validate.errors) {
        for (const err of validate.errors) {
          errors.push({
            code: `SCHEMA_${err.keyword?.toUpperCase() ?? 'ERROR'}`,
            message: err.message ?? 'Unknown schema error',
            path: err.instancePath ?? '',
          });
        }
      }

      return { isValid: true, errors: [] };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);

      // Check for specific schema validation errors
      if (errorMessage.includes('type')) {
        errors.push({
          code: 'SCHEMA_INVALID_TYPE',
          message: errorMessage,
          path: '',
        });
      } else {
        errors.push({
          code: 'SCHEMA_COMPILATION_ERROR',
          message: errorMessage,
          path: '',
        });
      }

      return { isValid: false, errors };
    }
  }

  /**
   * Validate data against a schema
   */
  validateData(data: unknown, schema: Record<string, unknown>): SchemaValidationResult {
    const errors: ValidationError[] = [];

    try {
      const validate = this.ajv.compile(schema);
      const valid = validate(data);

      if (!valid && validate.errors) {
        for (const err of validate.errors) {
          errors.push({
            code: `DATA_${err.keyword?.toUpperCase() ?? 'ERROR'}`,
            message: err.message ?? 'Unknown validation error',
            path: err.instancePath ?? '',
          });
        }
      }

      return { isValid: valid ?? false, errors };
    } catch (error) {
      errors.push({
        code: 'VALIDATION_ERROR',
        message: error instanceof Error ? error.message : String(error),
        path: '',
      });

      return { isValid: false, errors };
    }
  }

  /**
   * Convert YAML-style responseSchema to JSON Schema format
   *
   * YAML format (from capability files):
   * ```yaml
   * responseSchema:
   *   search_results:
   *     type: array
   *     description: Results
   *   count:
   *     type: integer
   * ```
   *
   * JSON Schema format:
   * ```json
   * {
   *   "type": "object",
   *   "properties": {
   *     "search_results": { "type": "array" },
   *     "count": { "type": "integer" }
   *   }
   * }
   * ```
   */
  convertToJsonSchema(yamlSchema: ResponseSchema): Record<string, unknown> {
    // If it's already in JSON Schema format
    if (yamlSchema.type && typeof yamlSchema.type === 'string') {
      return yamlSchema as unknown as Record<string, unknown>;
    }

    // Convert YAML-style to JSON Schema
    const properties: Record<string, ResponseSchemaProperty> = {};

    for (const [key, value] of Object.entries(yamlSchema)) {
      properties[key] = this.convertProperty(value);
    }

    return {
      type: 'object',
      properties,
    };
  }

  /**
   * Convert a single property to JSON Schema format
   */
  private convertProperty(prop: ResponseSchemaProperty): ResponseSchemaProperty {
    const converted: ResponseSchemaProperty = {
      type: prop.type,
    };

    if (prop.description) {
      converted.description = prop.description;
    }

    if (prop.format) {
      converted.format = prop.format;
    }

    if (prop.minimum !== undefined) {
      converted.minimum = prop.minimum;
    }

    if (prop.maximum !== undefined) {
      converted.maximum = prop.maximum;
    }

    if (prop.pattern) {
      converted.pattern = prop.pattern;
    }

    if (prop.enum) {
      converted.enum = prop.enum;
    }

    if (prop.items) {
      converted.items = this.convertProperty(prop.items);
    }

    if (prop.properties) {
      const nestedProperties: Record<string, ResponseSchemaProperty> = {};
      for (const [key, value] of Object.entries(prop.properties)) {
        nestedProperties[key] = this.convertProperty(value);
      }
      converted.properties = nestedProperties;
    }

    if (prop.required) {
      converted.required = prop.required;
    }

    return converted;
  }
}

/**
 * Factory function for creating ResponseSchemaValidator
 */
export function createResponseSchemaValidator(): ResponseSchemaValidator {
  return new ResponseSchemaValidator();
}
