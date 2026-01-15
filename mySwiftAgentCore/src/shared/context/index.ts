/**
 * Context Manager - Re-exports all context management components
 *
 * Provides a Facade pattern for accessing context management functionality:
 * - ExecutionContext: Execution state management
 * - VariableResolver: Variable resolution
 * - SecretManager: Secret management
 * - ValidationCoordinator: Validation coordination
 */

export {
  ExecutionContext,
  createExecutionContext,
  type ExecutionState,
  type ExecutionContextOptions,
} from './ExecutionContext.js';

export {
  VariableResolver,
  createVariableResolver,
  type VariableSource,
  type VariableReference,
  type ResolutionResult,
} from './VariableResolver.js';

export {
  SecretManager,
  createSecretManager,
  createSecretManagerFromEnv,
  type SecretProvider,
  type MyVaultConfig,
  type SecretManagerConfig,
} from './SecretManager.js';

export {
  ValidationCoordinator,
  createValidationCoordinator,
  type ValidationRule,
  type ValidationContext,
  type ValidationResult,
} from './ValidationCoordinator.js';
