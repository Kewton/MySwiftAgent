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
  expectedOutput: unknown;
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
