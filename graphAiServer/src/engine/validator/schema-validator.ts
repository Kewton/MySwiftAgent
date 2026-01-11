/**
 * Schema Validator for TaskFlow Engine
 *
 * This module provides I/O schema validation for node inputs and outputs.
 * It validates data against the simple type schema defined in workflow definitions.
 *
 * @module engine/validator/schema-validator
 * @see Issue #348
 */

import type { IOSchemaType, SimpleType, ValidationResult, ValidationError } from '../../types/taskflow.js';

// ============================================================
// Type Checking Functions
// ============================================================

/**
 * Get the simple type of a value
 * @param value - Value to check
 * @returns SimpleType string
 */
function getSimpleType(value: unknown): SimpleType {
  if (value === null) {
    return 'null';
  }

  if (Array.isArray(value)) {
    return 'array';
  }

  const type = typeof value;

  switch (type) {
    case 'string':
      return 'string';
    case 'number':
      return 'number';
    case 'boolean':
      return 'boolean';
    case 'object':
      return 'object';
    default:
      return 'null';
  }
}

/**
 * Check if a value matches a simple type
 * @param value - Value to check
 * @param expectedType - Expected simple type
 * @returns true if the value matches the type
 */
function matchesType(value: unknown, expectedType: SimpleType): boolean {
  const actualType = getSimpleType(value);

  // Exact type match
  if (actualType === expectedType) {
    return true;
  }

  // Allow null for any type (optional fields)
  if (actualType === 'null') {
    return true;
  }

  return false;
}

// ============================================================
// Schema Validator Class
// ============================================================

/**
 * Schema Validator for I/O validation
 */
export class SchemaValidator {
  /**
   * Validate input data against an input schema
   * @param schema - Input schema definition
   * @param data - Data to validate
   * @returns Validation result
   */
  validateInput(schema: IOSchemaType, data: unknown): ValidationResult {
    return this.validate(schema, data, 'input');
  }

  /**
   * Validate output data against an output schema
   * @param schema - Output schema definition
   * @param data - Data to validate
   * @returns Validation result
   */
  validateOutput(schema: IOSchemaType, data: unknown): ValidationResult {
    return this.validate(schema, data, 'output');
  }

  /**
   * Validate data against a schema
   * @param schema - Schema definition
   * @param data - Data to validate
   * @param context - Context for error messages ('input' or 'output')
   * @returns Validation result
   */
  private validate(
    schema: IOSchemaType,
    data: unknown,
    context: 'input' | 'output'
  ): ValidationResult {
    const errors: ValidationError[] = [];

    // Data must be an object
    if (data === null || typeof data !== 'object' || Array.isArray(data)) {
      errors.push({
        type: 'type',
        path: '',
        message: `${context} must be an object`,
        expected: 'object',
        actual: getSimpleType(data),
      });
      return { valid: false, errors };
    }

    const dataObj = data as Record<string, unknown>;

    // Check each field in the schema
    for (const [fieldName, expectedType] of Object.entries(schema)) {
      const value = dataObj[fieldName];

      // Check if field exists
      if (value === undefined) {
        errors.push({
          type: 'required',
          path: fieldName,
          message: `Missing required field: ${fieldName}`,
          expected: expectedType,
        });
        continue;
      }

      // Check type
      if (!matchesType(value, expectedType)) {
        const actualType = getSimpleType(value);
        errors.push({
          type: 'type',
          path: fieldName,
          message: `Field '${fieldName}' has wrong type`,
          expected: expectedType,
          actual: actualType,
        });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Validate partial data (allowing missing fields)
   * Useful for validating params before resolution
   * @param schema - Schema definition
   * @param data - Data to validate
   * @returns Validation result
   */
  validatePartial(schema: IOSchemaType, data: unknown): ValidationResult {
    const errors: ValidationError[] = [];

    if (data === null || typeof data !== 'object' || Array.isArray(data)) {
      errors.push({
        type: 'type',
        path: '',
        message: 'Data must be an object',
        expected: 'object',
        actual: getSimpleType(data),
      });
      return { valid: false, errors };
    }

    const dataObj = data as Record<string, unknown>;

    // Only check types for fields that exist
    for (const [fieldName, expectedType] of Object.entries(schema)) {
      const value = dataObj[fieldName];

      if (value !== undefined && !matchesType(value, expectedType)) {
        const actualType = getSimpleType(value);
        errors.push({
          type: 'type',
          path: fieldName,
          message: `Field '${fieldName}' has wrong type`,
          expected: expectedType,
          actual: actualType,
        });
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }
}

// ============================================================
// Exported Functions
// ============================================================

/** Global schema validator instance */
export const schemaValidator = new SchemaValidator();

/**
 * Validate input data against a schema
 * @param schema - Input schema
 * @param data - Data to validate
 * @returns Validation result
 */
export function validateInput(schema: IOSchemaType, data: unknown): ValidationResult {
  return schemaValidator.validateInput(schema, data);
}

/**
 * Validate output data against a schema
 * @param schema - Output schema
 * @param data - Data to validate
 * @returns Validation result
 */
export function validateOutput(schema: IOSchemaType, data: unknown): ValidationResult {
  return schemaValidator.validateOutput(schema, data);
}

/**
 * Format validation errors as human-readable strings
 * @param errors - Array of validation errors
 * @returns Formatted error messages
 */
export function formatValidationErrors(errors: ValidationError[]): string[] {
  return errors.map((error) => {
    const path = error.path ? `at '${error.path}'` : '';
    const expected = error.expected ? `, expected ${error.expected}` : '';
    const actual = error.actual ? `, got ${error.actual}` : '';
    return `${error.message}${path}${expected}${actual}`;
  });
}
