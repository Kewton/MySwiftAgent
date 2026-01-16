/**
 * TaskFlow Engine - Main entry point
 *
 * Issue #363: TaskFlow execution engine for mySwiftAgentCore
 *
 * This module provides:
 * - Type definitions (TaskFlowDefinition, InternalWorkflowDefinition)
 * - Adapter for type conversion
 * - Registry for workflow management
 * - Loader for filesystem-based workflows
 * - Sandbox for secure JavaScript execution
 * - Node executors (api_rest, transform, code_js, llm, parallel)
 * - Parallel execution management
 * - Schema validation
 * - Langfuse tracing integration
 * - REST API handlers
 * - TypeScript SDK client
 *
 * @module taskflowEngine
 */

// Main Engine Facade
export * from './TaskFlowEngine.js';

// Types
export * from './types/index.js';

// Adapter
export * from './adapter/index.js';

// Registry
export * from './registry/index.js';

// Loader
export * from './loader/index.js';

// Sandbox
export * from './sandbox/index.js';

// Nodes
export * from './nodes/index.js';

// Executor
export * from './executor/index.js';

// Validator
export * from './validator/index.js';

// Tracer
export * from './tracer/index.js';

// API
export * from './api/index.js';

// Client
export * from './client/index.js';

// Re-export key types from shared
export type {
  WorkflowExecutionResult,
  StepResult,
  StepError,
  ExecutionStatus,
} from '../shared/types/workflow.types.js';
