/**
 * Base Node Abstract Class
 *
 * This module provides the abstract base class for all TaskFlow node types.
 * It implements the Template Method pattern for common execution flow.
 *
 * @module nodes/base-node
 * @see Issue #348
 */

import type {
  BaseStep,
  NodeConfig,
  NodeResult,
  NodeLog,
  NodeState,
  NodeError,
  IOSchemaType,
} from '../types/taskflow.js';
import { ContextManager } from '../engine/context/context-manager.js';
import { schemaValidator, formatValidationErrors } from '../engine/validator/schema-validator.js';

// ============================================================
// Base Node Abstract Class
// ============================================================

/**
 * Abstract base class for all TaskFlow nodes
 *
 * Implements the Template Method pattern:
 * 1. Pre-execution: Resolve params and validate input
 * 2. Execution: Execute node-specific logic (abstract)
 * 3. Post-execution: Validate output and build result
 */
export abstract class BaseNode<T extends NodeConfig = NodeConfig> {
  /** Node ID */
  public readonly id: string;

  /** Node type */
  public readonly type: string;

  /** Node description */
  public readonly description?: string;

  /** Node configuration */
  public readonly config: T;

  /** Input parameters (with variable references) */
  public readonly params: Record<string, unknown>;

  /** Input schema for validation */
  public readonly inputSchema?: IOSchemaType;

  /** Output schema for validation */
  public readonly outputSchema?: IOSchemaType;

  constructor(step: BaseStep) {
    this.id = step.id;
    this.type = step.type;
    this.description = step.description;
    this.config = step.config as T;
    this.params = step.params || {};
    this.inputSchema = step.input_schema;
    this.outputSchema = step.output_schema;
  }

  /**
   * Execute the node with full lifecycle management
   * @param context - Execution context
   * @returns Node execution result
   */
  async execute(context: ContextManager): Promise<NodeResult> {
    const startTime = Date.now();
    let state: NodeState = 'running';

    try {
      // 1. Resolve parameters
      const resolvedParams = await this.resolveParams(context);

      // 2. Validate input (if schema provided)
      if (this.inputSchema) {
        const inputValidation = schemaValidator.validateInput(
          this.inputSchema,
          resolvedParams
        );
        if (!inputValidation.valid) {
          const errorMessages = formatValidationErrors(inputValidation.errors);
          throw new InputValidationError(
            `Input validation failed: ${errorMessages.join('; ')}`,
            inputValidation.errors
          );
        }
      }

      // 3. Execute node-specific logic
      const output = await this.executeInternal(resolvedParams, context);

      // 4. Validate output (if schema provided)
      if (this.outputSchema) {
        const outputValidation = schemaValidator.validateOutput(
          this.outputSchema,
          output
        );
        if (!outputValidation.valid) {
          const errorMessages = formatValidationErrors(outputValidation.errors);
          throw new OutputValidationError(
            `Output validation failed: ${errorMessages.join('; ')}`,
            outputValidation.errors
          );
        }
      }

      // 5. Store output in context
      context.setOutput(this.id, output);
      state = 'completed';

      const endTime = Date.now();

      return {
        success: true,
        output,
        log: this.buildLog(state, startTime, endTime),
      };
    } catch (error) {
      const endTime = Date.now();
      state = 'failed';

      const nodeError = this.buildError(error);
      context.setError(this.id, nodeError);

      return {
        success: false,
        error: nodeError,
        log: this.buildLog(state, startTime, endTime, nodeError),
      };
    }
  }

  /**
   * Abstract method for node-specific execution logic
   * Must be implemented by subclasses
   * @param params - Resolved parameters
   * @param context - Execution context
   * @returns Node output
   */
  protected abstract executeInternal(
    params: Record<string, unknown>,
    context: ContextManager
  ): Promise<unknown>;

  /**
   * Resolve all variable references in params
   * @param context - Execution context
   * @returns Resolved parameters
   */
  protected async resolveParams(context: ContextManager): Promise<Record<string, unknown>> {
    const resolved: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(this.params)) {
      resolved[key] = await context.resolve(value);
    }

    return resolved;
  }

  /**
   * Build a node execution log entry
   * @param state - Execution state
   * @param startTime - Start timestamp
   * @param endTime - End timestamp
   * @param error - Error details (if failed)
   * @returns Node log entry
   */
  protected buildLog(
    state: NodeState,
    startTime: number,
    endTime: number,
    error?: NodeError
  ): NodeLog {
    const log: NodeLog = {
      nodeId: this.id,
      state,
      startTime,
      endTime,
      retryCount: 0,
    };

    if (error) {
      log.error = {
        message: error.message,
        stack: error.stack,
      };
    }

    return log;
  }

  /**
   * Build a NodeError from an exception
   * @param error - Caught exception
   * @returns Formatted NodeError
   */
  protected buildError(error: unknown): NodeError {
    if (error instanceof NodeExecutionError) {
      return {
        message: error.message,
        code: error.code,
        stack: error.stack,
        details: error.details,
      };
    }

    if (error instanceof Error) {
      return {
        message: error.message,
        stack: error.stack,
        code: 'EXECUTION_ERROR',
      };
    }

    return {
      message: String(error),
      code: 'UNKNOWN_ERROR',
    };
  }
}

// ============================================================
// Error Classes
// ============================================================

/**
 * Base error class for node execution errors
 */
export class NodeExecutionError extends Error {
  public readonly code: string;
  public readonly details?: Record<string, unknown>;

  constructor(message: string, code: string, details?: Record<string, unknown>) {
    super(message);
    this.name = 'NodeExecutionError';
    this.code = code;
    this.details = details;
  }
}

/**
 * Error thrown when input validation fails
 */
export class InputValidationError extends NodeExecutionError {
  constructor(message: string, errors: unknown[]) {
    super(message, 'INPUT_VALIDATION_ERROR', { validationErrors: errors });
    this.name = 'InputValidationError';
  }
}

/**
 * Error thrown when output validation fails
 */
export class OutputValidationError extends NodeExecutionError {
  constructor(message: string, errors: unknown[]) {
    super(message, 'OUTPUT_VALIDATION_ERROR', { validationErrors: errors });
    this.name = 'OutputValidationError';
  }
}

/**
 * Error thrown when API request fails
 */
export class ApiError extends NodeExecutionError {
  public readonly statusCode?: number;
  public readonly responseBody?: unknown;

  constructor(
    message: string,
    statusCode?: number,
    responseBody?: unknown,
    details?: Record<string, unknown>
  ) {
    super(message, 'API_ERROR', {
      ...details,
      status_code: statusCode,
      response_body: responseBody,
    });
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.responseBody = responseBody;
  }
}

/**
 * Error thrown for timeout conditions
 */
export class TimeoutError extends NodeExecutionError {
  constructor(message: string, timeoutMs: number) {
    super(message, 'TIMEOUT_ERROR', { timeout_ms: timeoutMs });
    this.name = 'TimeoutError';
  }
}

/**
 * Error thrown for JavaScript execution errors
 */
export class ScriptExecutionError extends NodeExecutionError {
  constructor(message: string, scriptPath?: string, functionName?: string) {
    super(message, 'SCRIPT_EXECUTION_ERROR', {
      script_path: scriptPath,
      function_name: functionName,
    });
    this.name = 'ScriptExecutionError';
  }
}

/**
 * Error thrown for template processing errors
 */
export class TemplateError extends NodeExecutionError {
  constructor(message: string, template?: string) {
    super(message, 'TEMPLATE_ERROR', { template });
    this.name = 'TemplateError';
  }
}
