/**
 * Validation Types - Extended types for Issue #381
 *
 * Issue #381: Enhanced validation types for component integrity checking
 *
 * Features:
 * - ErrorSuggestion for improved error messages
 * - ValidationErrorContext for detailed error information
 * - SharedValidationCache for performance optimization
 * - ValidationObserver for debug mode
 * - CircularReferenceInfo and PerformanceMetrics for diagnostics
 */

import type {
  ValidationResult,
  ValidationError,
  Capability,
  ResponseSchema,
} from './generator.js';
import type { ValidationContext } from '../validator/ValidationPipeline.js';
import type { TaskFlowStep } from '../../taskflowEngine/types/TaskFlowDefinition.js';

/**
 * Error codes for workflow validation
 */
export type ComponentValidationErrorCode =
  | 'CAPABILITY_NOT_FOUND'
  | 'OUTPUT_FIELD_NOT_FOUND'
  | 'TEMPLATE_SYNTAX_ERROR'
  | 'SCHEMA_MISMATCH'
  | 'CIRCULAR_REFERENCE_DETECTED'
  | 'STEP_REFERENCE_NOT_FOUND';

/**
 * ErrorSuggestion - Detailed fix suggestions for validation errors
 */
export interface ErrorSuggestion {
  /** Main suggestion message */
  message: string;
  /** List of available options (e.g., available fields/steps) */
  availableOptions?: string[];
  /** Closest matching option (Levenshtein distance) */
  closestMatch?: string;
  /** Example of correct usage */
  example?: string;
  /** URL to relevant documentation */
  documentationUrl?: string;
}

/**
 * ValidationErrorContext - Contextual information about validation errors
 */
export interface ValidationErrorContext {
  /** Step ID where the error originated */
  sourceStep?: string;
  /** Target step ID being referenced */
  targetStep?: string;
  /** Full reference path that caused the error */
  referencePath?: string;
  /** Expected type for schema errors */
  expectedType?: string;
  /** Actual type found */
  actualType?: string;
  /** Path of circular reference (for circular dependency errors) */
  circularPath?: string[];
}

/**
 * ComponentValidationError - Extended validation error with suggestions
 */
export interface ComponentValidationError extends ValidationError {
  /** Step ID where the error occurred */
  stepId: string;
  /** Field name related to the error */
  field: string;
  /** Specific error code for the workflow error */
  errorCode: ComponentValidationErrorCode;
  /** Suggestion for fixing the error */
  suggestion?: ErrorSuggestion;
  /** Additional context about the error */
  context?: ValidationErrorContext;
}

/**
 * SharedValidationCache - Cached data shared across validators
 */
export interface SharedValidationCache {
  /** Map of capability ID to capability definition */
  capabilityMap: Map<string, Capability>;
  /** Map of step ID to step definition */
  stepMap: Map<string, TaskFlowStep>;
  /** Map of capability ID to response schema */
  responseSchemaMap: Map<string, ResponseSchema>;
}

/**
 * ValidationObserver - Observer interface for debug mode
 */
export interface ValidationObserver {
  /** Called when a validator starts */
  onValidatorStart(validatorName: string): void;
  /** Called when a validator completes */
  onValidatorComplete(
    validatorName: string,
    result: ValidationResult,
    durationMs: number
  ): void;
  /** Called when a validator throws an error */
  onError(validatorName: string, error: Error): void;
}

/**
 * CircularReferenceInfo - Information about detected circular references
 */
export interface CircularReferenceInfo {
  /** Path showing the circular dependency chain */
  path: string[];
  /** Severity of the circular reference */
  severity: 'error' | 'warning';
  /** Suggestion for fixing the circular reference */
  suggestion: string;
}

/**
 * ValidatorMetric - Performance metric for a single validator
 */
export interface ValidatorMetric {
  /** Time taken in milliseconds */
  durationMs: number;
  /** Number of errors found */
  errorsFound: number;
}

/**
 * PerformanceMetrics - Performance data for validation run
 */
export interface PerformanceMetrics {
  /** Total validation duration in milliseconds */
  totalDurationMs: number;
  /** Per-validator metrics */
  validatorMetrics: Map<string, ValidatorMetric>;
  /** Number of steps analyzed */
  stepsAnalyzed: number;
  /** Number of references checked */
  referencesChecked: number;
}

/**
 * ComponentValidationResult - Extended validation result with component details
 */
export interface ComponentValidationResult extends ValidationResult {
  /** Errors grouped by component/step */
  componentErrors?: Map<string, ComponentValidationError[]>;
  /** Errors involving cross-step references */
  crossStepErrors?: ComponentValidationError[];
  /** Information about detected circular references */
  circularReferences?: CircularReferenceInfo[];
  /** Performance metrics (when debug mode is enabled) */
  performanceMetrics?: PerformanceMetrics;
}

/**
 * EnhancedValidationContext - Extended validation context with additional options
 */
export interface EnhancedValidationContext extends ValidationContext {
  /** Additional context options */
  additionalContext?: {
    /** Enable template syntax validation (default: true) */
    enableTemplateValidation?: boolean;
    /** Enable schema compatibility checking */
    enableSchemaCompatibilityCheck?: boolean;
    /** Enable error propagation checking */
    enableErrorPropagationCheck?: boolean;
    /** Strict mode - treat warnings as errors */
    strictMode?: boolean;
    /** Enable circular reference detection (default: true) */
    enableCircularReferenceCheck?: boolean;
    /** Maximum depth for circular reference detection (default: 10) */
    maxCircularDepth?: number;
    /** Enable debug mode */
    debugMode?: boolean;
    /** Enable verbose error messages */
    verboseErrors?: boolean;
    /** Collect performance metrics */
    collectPerformanceMetrics?: boolean;
    /** Validation observer for callbacks */
    validationObserver?: ValidationObserver;
  };
  /** Shared cache for performance optimization */
  sharedCache?: SharedValidationCache;
}

/**
 * StepReference - Parsed step reference information
 */
export interface StepReference {
  /** Referenced step ID */
  stepId: string;
  /** Referenced field name */
  fieldName: string;
  /** Full reference path (e.g., "$steps.step_001.result") */
  fullPath: string;
}

/**
 * ComponentValidator - Interface for sub-validators in ComponentIntegrityValidator
 */
export interface ComponentValidator {
  /** Validator name */
  readonly name: string;
  /** Validate workflow and return result */
  validate(
    workflow: import('../../taskflowEngine/types/TaskFlowDefinition.js').TaskFlowDefinition,
    context: EnhancedValidationContext
  ): Promise<ValidationResult>;
}

/**
 * ValidationLog - Log entry for debug observer
 */
export interface ValidationLog {
  /** Validator name */
  validatorName: string;
  /** Validation result */
  result: ValidationResult;
  /** Duration in milliseconds */
  durationMs: number;
  /** Timestamp of completion */
  timestamp: Date;
}
