/**
 * Capability Types - Type definitions for capability management
 *
 * This module defines types for managing agent capabilities,
 * including registration, discovery, and invocation.
 */

import { z } from 'zod';

/**
 * Capability status
 */
export type CapabilityStatus = 'available' | 'unavailable' | 'deprecated';

/**
 * Parameter type definitions
 */
export type ParameterType = 'string' | 'number' | 'boolean' | 'object' | 'array';

/**
 * Capability parameter definition
 */
export interface CapabilityParameter {
  name: string;
  type: ParameterType;
  required: boolean;
  description: string;
  defaultValue?: unknown;
  validation?: {
    pattern?: string;
    min?: number;
    max?: number;
    enum?: unknown[];
  };
}

/**
 * Capability definition
 */
export interface Capability {
  id: string;
  name: string;
  description: string;
  version: string;
  status: CapabilityStatus;
  category: string;
  parameters: CapabilityParameter[];
  returnType: ParameterType;
  examples?: CapabilityExample[];
  tags?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Capability example for documentation
 */
export interface CapabilityExample {
  description: string;
  input: Record<string, unknown>;
  expectedOutput?: unknown;
}

/**
 * Capability invocation request
 */
export interface CapabilityInvocationRequest {
  capabilityId: string;
  parameters: Record<string, unknown>;
  context?: Record<string, unknown>;
  timeout?: number;
}

/**
 * Capability invocation result
 */
export interface CapabilityInvocationResult {
  capabilityId: string;
  status: 'success' | 'failed';
  result?: unknown;
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  durationMs: number;
  metadata?: Record<string, unknown>;
}

/**
 * Capability registry entry
 */
export interface CapabilityRegistryEntry {
  capability: Capability;
  registeredAt: Date;
  lastUpdatedAt: Date;
  usageCount: number;
}

// ============================================
// Issue #365: Project-based Capability Management
// ============================================

/**
 * HTTP method types for API endpoints
 */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';

/**
 * Authentication type for capability endpoints
 */
export type AuthType = 'api_key' | 'bearer_token' | 'basic' | 'oauth2' | 'none';

/**
 * Internal implementation details (not exposed to clients)
 * Contains sensitive information like endpoints and authentication
 */
export interface CapabilityInternal {
  /** API endpoint URL */
  endpoint?: string;
  /** HTTP method */
  method?: HttpMethod;
  /** Authentication type */
  auth_type?: AuthType;
  /** MyVault secret key reference */
  secret_key?: string;
  /** Custom headers */
  headers?: Record<string, string>;
  /** Timeout in milliseconds */
  timeout_ms?: number;
  /** Additional internal configuration */
  config?: Record<string, unknown>;
}

/**
 * Extended capability with project association and internal details
 * Used for full capability representation including sensitive data
 */
export interface CapabilityExtended extends Capability {
  /** Project this capability belongs to */
  project?: string;
  /** Internal implementation details (not exposed to clients) */
  _internal?: CapabilityInternal;
}

/**
 * Raw capability as loaded from YAML files
 * Includes all fields including _internal section
 */
export type RawCapability = CapabilityExtended;

/**
 * Public capability for client responses
 * Excludes _internal section for security
 */
export type PublicCapability = Omit<CapabilityExtended, '_internal'>;

/**
 * Result of loading capabilities from files
 * Supports partial success scenarios
 */
export interface CapabilityLoadResult {
  /** Successfully loaded capabilities */
  successful: CapabilityExtended[];
  /** Failed capability loads */
  failed: Array<{
    /** File path that failed to load */
    file: string;
    /** Error message */
    error: string;
    /** Error details */
    details?: unknown;
  }>;
  /** Total files attempted */
  totalAttempted: number;
  /** Whether any capabilities were loaded */
  hasCapabilities: boolean;
}

/**
 * Project capabilities container
 */
export interface ProjectCapabilities {
  /** Project identifier */
  projectId: string;
  /** Project display name */
  name: string;
  /** Project description */
  description?: string;
  /** Capabilities in this project */
  capabilities: Map<string, CapabilityExtended>;
  /** References to shared capabilities */
  sharedRefs: string[];
  /** Project creation date */
  createdAt: Date;
  /** Last updated date */
  updatedAt: Date;
}

/**
 * Capability filter with project support
 */
export interface CapabilityFilterExtended {
  /** Filter by project */
  project?: string;
  /** Filter by category */
  category?: string;
  /** Filter by status */
  status?: CapabilityStatus;
  /** Filter by tags */
  tags?: string[];
  /** Search term for name/description */
  searchTerm?: string;
  /** Include shared capabilities */
  includeShared?: boolean;
}

// Zod schemas for validation

export const CapabilityParameterSchema = z.object({
  name: z.string(),
  type: z.enum(['string', 'number', 'boolean', 'object', 'array']),
  required: z.boolean(),
  description: z.string(),
  defaultValue: z.unknown().optional(),
  validation: z
    .object({
      pattern: z.string().optional(),
      min: z.number().optional(),
      max: z.number().optional(),
      enum: z.array(z.unknown()).optional(),
    })
    .optional(),
});

export const CapabilitySchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.string(),
  status: z.enum(['available', 'unavailable', 'deprecated']),
  category: z.string(),
  parameters: z.array(CapabilityParameterSchema),
  returnType: z.enum(['string', 'number', 'boolean', 'object', 'array']),
  examples: z
    .array(
      z.object({
        description: z.string(),
        input: z.record(z.unknown()),
        expectedOutput: z.unknown(),
      })
    )
    .optional(),
  tags: z.array(z.string()).optional(),
  metadata: z.record(z.unknown()).optional(),
});

export const CapabilityInvocationRequestSchema = z.object({
  capabilityId: z.string(),
  parameters: z.record(z.unknown()),
  context: z.record(z.unknown()).optional(),
  timeout: z.number().optional(),
});

export const CapabilityInvocationResultSchema = z.object({
  capabilityId: z.string(),
  status: z.enum(['success', 'failed']),
  result: z.unknown().optional(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
      details: z.unknown().optional(),
    })
    .optional(),
  durationMs: z.number(),
  metadata: z.record(z.unknown()).optional(),
});

// ============================================
// Issue #365: Extended Zod Schemas
// ============================================

/**
 * HTTP method schema
 */
export const HttpMethodSchema = z.enum(['GET', 'POST', 'PUT', 'DELETE', 'PATCH']);

/**
 * Authentication type schema
 */
export const AuthTypeSchema = z.enum(['api_key', 'bearer_token', 'basic', 'oauth2', 'none']);

/**
 * Internal implementation details schema
 * Used for validating YAML _internal sections
 */
export const CapabilityInternalSchema = z.object({
  endpoint: z.string().url().optional(),
  method: HttpMethodSchema.optional(),
  auth_type: AuthTypeSchema.optional(),
  secret_key: z.string().optional(),
  headers: z.record(z.string()).optional(),
  timeout_ms: z.number().positive().optional(),
  config: z.record(z.unknown()).optional(),
});

/**
 * Extended capability schema with project and internal details
 */
export const CapabilityExtendedSchema = CapabilitySchema.extend({
  project: z.string().optional(),
  _internal: CapabilityInternalSchema.optional(),
});

/**
 * Raw capability schema (for YAML loading)
 */
export const RawCapabilitySchema = CapabilityExtendedSchema;

/**
 * Public capability schema (excludes _internal)
 */
export const PublicCapabilitySchema = CapabilitySchema.extend({
  project: z.string().optional(),
});

/**
 * Capability load result schema
 */
export const CapabilityLoadResultSchema = z.object({
  successful: z.array(CapabilityExtendedSchema),
  failed: z.array(
    z.object({
      file: z.string(),
      error: z.string(),
      details: z.unknown().optional(),
    })
  ),
  totalAttempted: z.number(),
  hasCapabilities: z.boolean(),
});

/**
 * Extended filter schema with project support
 */
export const CapabilityFilterExtendedSchema = z.object({
  project: z.string().optional(),
  category: z.string().optional(),
  status: z.enum(['available', 'unavailable', 'deprecated']).optional(),
  tags: z.array(z.string()).optional(),
  searchTerm: z.string().optional(),
  includeShared: z.boolean().optional(),
});
