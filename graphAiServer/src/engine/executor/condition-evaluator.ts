/**
 * Condition Evaluator for TaskFlow Engine
 *
 * Provides secure evaluation of condition expressions for conditional branching.
 * Uses whitelist approach to prevent code injection attacks.
 *
 * Security Features:
 * 1. Whitelist approach - only primitive values allowed
 * 2. No eval() or new Function() usage
 * 3. No JSON.parse for arbitrary objects
 * 4. Strict regex pattern for expression parsing
 *
 * @module engine/executor/condition-evaluator
 * @see Issue #348
 */

import { ContextManager } from '../context/context-manager.js';

// ============================================================
// Types
// ============================================================

/**
 * Allowed comparison operators
 */
export type ComparisonOperator = '==' | '!=' | '>' | '<' | '>=' | '<=';

/**
 * Allowed primitive value types
 */
export type AllowedPrimitive = string | number | boolean | null;

/**
 * Condition evaluation result
 */
export interface ConditionEvaluationResult {
  /** The boolean result of the condition */
  result: boolean;
  /** Evaluated condition string for debugging */
  evaluatedCondition: string;
  /** Error message if evaluation failed */
  error?: string;
}

/**
 * Parsed condition structure
 */
export interface ParsedCondition {
  /** Variable path (e.g., "user.output.status") */
  variable: string;
  /** Comparison operator */
  operator: ComparisonOperator;
  /** Right-hand side value */
  value: AllowedPrimitive;
}

// ============================================================
// Expression Parsing
// ============================================================

/**
 * Parse a condition expression string into structured components.
 *
 * Accepts format: ${variable.path} OPERATOR VALUE
 *
 * Where:
 * - variable.path: dot-separated path (alphanumeric + underscore)
 * - OPERATOR: ==, !=, >, <, >=, <=
 * - VALUE: string literal, number, boolean, or null
 *
 * @param expr - Condition expression string
 * @returns Parsed condition or null if invalid
 */
export function parseConditionExpression(expr: string): ParsedCondition | null {
  // Pattern explanation:
  // ^\$\{([a-zA-Z_][a-zA-Z0-9_.]*)\}  - ${variable.path}
  // \s*(==|!=|>=|<=|>|<)\s*           - comparison operator with optional whitespace
  //                                     Note: >= and <= must come before > and < in the pattern
  // (.+)$                              - right-hand value (parsed separately)
  const pattern = /^\$\{([a-zA-Z_][a-zA-Z0-9_.]*)\}\s*(==|!=|>=|<=|>|<)\s*(.+)$/;
  const match = expr.trim().match(pattern);

  if (!match) {
    return null;
  }

  const [, variable, operator, rawValue] = match;
  const value = parseAllowedValue(rawValue.trim());

  // Return null if value is not in allowed format
  if (value === undefined) {
    return null;
  }

  return {
    variable,
    operator: operator as ComparisonOperator,
    value,
  };
}

/**
 * Parse a value string into an allowed primitive type.
 *
 * Allowed values:
 * - String literals: 'value' or "value"
 * - Numbers: 123, -45.67
 * - Booleans: true, false
 * - Null: null
 *
 * Security: Objects, arrays, and arbitrary expressions are rejected.
 *
 * @param rawValue - Raw value string
 * @returns Parsed primitive value or undefined if not allowed
 */
export function parseAllowedValue(rawValue: string): AllowedPrimitive | undefined {
  // Single-quoted string literal
  if (rawValue.startsWith("'") && rawValue.endsWith("'") && rawValue.length >= 2) {
    return rawValue.slice(1, -1);
  }

  // Double-quoted string literal
  if (rawValue.startsWith('"') && rawValue.endsWith('"') && rawValue.length >= 2) {
    return rawValue.slice(1, -1);
  }

  // Boolean true
  if (rawValue === 'true') {
    return true;
  }

  // Boolean false
  if (rawValue === 'false') {
    return false;
  }

  // Null
  if (rawValue === 'null') {
    return null;
  }

  // Number (integer or decimal, positive or negative)
  if (/^-?\d+(\.\d+)?$/.test(rawValue)) {
    return Number(rawValue);
  }

  // Not an allowed value
  return undefined;
}

// ============================================================
// Value Comparison
// ============================================================

/**
 * Compare two values using the specified operator.
 *
 * @param left - Left operand
 * @param operator - Comparison operator
 * @param right - Right operand
 * @returns Comparison result
 */
export function compareValues(
  left: AllowedPrimitive,
  operator: ComparisonOperator,
  right: AllowedPrimitive
): boolean {
  switch (operator) {
    case '==':
      return left === right;
    case '!=':
      return left !== right;
    case '>':
      return (left as number) > (right as number);
    case '<':
      return (left as number) < (right as number);
    case '>=':
      return (left as number) >= (right as number);
    case '<=':
      return (left as number) <= (right as number);
    default:
      return false;
  }
}

// ============================================================
// Variable Resolution
// ============================================================

/**
 * Resolve a variable path to a primitive value from context.
 *
 * @param variablePath - Dot-separated variable path
 * @param context - Execution context
 * @returns Resolved value as primitive
 */
function resolveVariableAsPrimitive(
  variablePath: string,
  context: ContextManager
): AllowedPrimitive {
  // Use context's resolution - build the reference string
  const reference = `\${${variablePath}}`;

  // Get the resolved value synchronously by accessing context directly
  const segments = variablePath.split('.');

  if (segments.length < 2) {
    return null;
  }

  const source = segments[0];
  let value: unknown;

  if (source === 'inputs') {
    value = getNestedValue(context.inputs, segments.slice(1));
  } else if (source === 'env') {
    value = context.env[segments[1]];
  } else {
    // Assume node output: node_id.output.field
    if (segments[1] === 'output') {
      const output = context.outputs.get(source);
      value = getNestedValue(output, segments.slice(2));
    } else {
      value = null;
    }
  }

  // Convert to primitive
  if (typeof value === 'string') return value;
  if (typeof value === 'number') return value;
  if (typeof value === 'boolean') return value;
  if (value === null) return null;
  if (value === undefined) return null;

  // Objects/arrays get stringified
  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  return String(value);
}

/**
 * Get a nested value from an object using a path array
 *
 * @param obj - Object to traverse
 * @param path - Array of path segments
 * @returns Value at path or undefined
 */
function getNestedValue(obj: unknown, path: string[]): unknown {
  let current: unknown = obj;

  for (const segment of path) {
    if (current === null || current === undefined) {
      return undefined;
    }

    if (typeof current === 'object' && current !== null) {
      current = (current as Record<string, unknown>)[segment];
    } else {
      return undefined;
    }
  }

  return current;
}

// ============================================================
// Main Evaluation Function
// ============================================================

/**
 * Evaluate a condition expression against execution context.
 *
 * Security: Uses whitelist approach - only primitive comparisons allowed.
 * No eval(), no Function(), no JSON.parse for arbitrary objects.
 *
 * @param condition - Condition expression (e.g., "${user.output.status} == 'active'")
 * @param context - Execution context with variable values
 * @returns Evaluation result with debugging information
 *
 * @example
 * // String comparison
 * evaluateCondition("${user.output.status} == 'active'", context)
 *
 * // Numeric comparison
 * evaluateCondition("${count.output.value} > 100", context)
 *
 * // Boolean comparison
 * evaluateCondition("${flag.output.enabled} == true", context)
 */
export function evaluateCondition(
  condition: string,
  context: ContextManager
): ConditionEvaluationResult {
  try {
    // 1. Parse the condition expression
    const parsed = parseConditionExpression(condition);

    if (!parsed) {
      return {
        result: false,
        evaluatedCondition: condition,
        error: 'Invalid condition expression format',
      };
    }

    // 2. Resolve the variable to a primitive value
    const leftValue = resolveVariableAsPrimitive(parsed.variable, context);
    const rightValue = parsed.value;

    // 3. Perform the comparison
    const result = compareValues(leftValue, parsed.operator, rightValue);

    return {
      result,
      evaluatedCondition: `${JSON.stringify(leftValue)} ${parsed.operator} ${JSON.stringify(rightValue)}`,
    };
  } catch (error) {
    return {
      result: false,
      evaluatedCondition: condition,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
