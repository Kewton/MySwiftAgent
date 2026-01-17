/**
 * Storage module exports
 *
 * Issue #370: Workflow persistence
 * Issue #373: Cache mechanism and taskId support
 */

export {
  WorkflowStorage,
  createWorkflowStorage,
  WorkflowStorageError,
  DEFAULT_CACHE_CONFIG,
  type WorkflowStorageConfig,
  type WorkflowCacheConfig,
  type SaveResult,
} from './WorkflowStorage.js';
