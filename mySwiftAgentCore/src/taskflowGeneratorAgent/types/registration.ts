/**
 * Registration Types - Type definitions for partial success model
 *
 * Issue #378: Partial success model for workflow registration
 *
 * Design Principles:
 * - status field provides 3-state response: 'success' | 'partial_success' | 'failed'
 * - success: boolean field maintained for backward compatibility
 * - Detailed tracking of memory registration vs storage persistence
 */

import { z } from 'zod';

/**
 * Registration Status enum
 *
 * - success: Both memory registration and storage persistence succeeded
 * - partial_success: Memory registration succeeded but storage persistence failed
 * - failed: Memory registration failed (workflow not available)
 */
export type RegistrationStatus = 'success' | 'partial_success' | 'failed';

export const RegistrationStatusSchema = z.enum(['success', 'partial_success', 'failed']);

/**
 * Detailed Registration Result - Result for a single workflow registration
 *
 * Issue #378: Provides detailed information about registration outcome
 */
export interface DetailedRegistrationResult {
  /** 3-state status: 'success' | 'partial_success' | 'failed' */
  status: RegistrationStatus;
  /** Backward-compatible success flag (status !== 'failed') */
  success: boolean;
  /** Workflow identifier */
  workflowId?: string;
  /** File path if persisted to storage */
  filePath?: string;
  /** Whether workflow is registered in memory (available for execution) */
  memoryRegistered: boolean;
  /** Whether workflow is persisted to storage (survives restart) */
  storagePersisted: boolean;
  /** Error message if failed */
  error?: string;
  /** Specific storage error if storage persistence failed */
  storageError?: string;
}

export const DetailedRegistrationResultSchema = z.object({
  status: RegistrationStatusSchema,
  success: z.boolean(),
  workflowId: z.string().optional(),
  filePath: z.string().optional(),
  memoryRegistered: z.boolean(),
  storagePersisted: z.boolean(),
  error: z.string().optional(),
  storageError: z.string().optional(),
});

/**
 * Batch Registration Summary - Summary for multiple workflow registrations
 *
 * Issue #378: Aggregated status for batch operations
 */
export interface BatchRegistrationSummary {
  /** Overall status based on individual results */
  status: RegistrationStatus;
  /** Backward-compatible success flag */
  success: boolean;
  /** Total number of workflows attempted */
  total: number;
  /** Number of fully successful registrations */
  succeeded: number;
  /** Number of partial successes (memory only) */
  partialSuccess: number;
  /** Number of complete failures */
  failed: number;
  /** Individual results keyed by workflow name or task_id */
  results: Record<string, DetailedRegistrationResult>;
}

export const BatchRegistrationSummarySchema = z.object({
  status: RegistrationStatusSchema,
  success: z.boolean(),
  total: z.number().int().min(0),
  succeeded: z.number().int().min(0),
  partialSuccess: z.number().int().min(0),
  failed: z.number().int().min(0),
  results: z.record(DetailedRegistrationResultSchema),
});

/**
 * Helper function to determine status from individual result counts
 *
 * @param succeeded - Number of fully successful operations
 * @param failed - Number of failed operations
 * @param total - Total number of operations
 * @returns RegistrationStatus
 */
export function determineStatus(
  succeeded: number,
  failed: number,
  total: number
): RegistrationStatus {
  // Empty case: consider as success
  if (total === 0) {
    return 'success';
  }

  // All failed
  if (succeeded === 0 && total > 0) {
    return 'failed';
  }

  // All succeeded
  if (failed === 0 && succeeded > 0) {
    return 'success';
  }

  // Mixed results
  return 'partial_success';
}
