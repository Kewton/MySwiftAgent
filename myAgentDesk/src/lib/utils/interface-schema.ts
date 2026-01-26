/**
 * Interface Schema Helpers
 * Issue #293: JobQueue Integration for Runs
 * Issue #410: Added getUserInputSchema for end-to-end schema propagation
 *
 * Utilities for parsing interface definitions from JobVersion
 * and merging task progress with interface metadata.
 */

import type { TaskDetail, TaskStatus } from '$lib/api/clients/job-queue';

// =============================================================================
// Type Definitions
// =============================================================================

/**
 * JSON Schema type for input/output definitions
 */
export interface JSONSchema {
	type: 'object' | 'string' | 'number' | 'boolean' | 'array';
	properties?: Record<
		string,
		{
			type: string;
			description?: string;
			default?: unknown;
			enum?: unknown[];
		}
	>;
	required?: string[];
	additionalProperties?: boolean;
}

/**
 * Task interface definition from JobVersion.interfaceDefinitions
 */
export interface TaskInterface {
	interface_master_id: string;
	input_interface_id: string;
	output_interface_id: string;
	interface_name: string;
	input_schema?: JSONSchema;
	output_schema?: JSONSchema;
}

/**
 * Interface definitions structure (task_001, task_002, etc.)
 */
export interface InterfaceDefinitions {
	[taskId: string]: TaskInterface;
}

/**
 * Task progress item for UI display
 */
export interface TaskProgressItem {
	taskId: string;
	taskName: string;
	order: number;
	status: TaskStatus | string;
	inputSchema?: JSONSchema;
	outputSchema?: JSONSchema;
	inputData?: Record<string, unknown> | null;
	outputData?: Record<string, unknown> | null;
	error?: string | null;
	startedAt?: Date;
	finishedAt?: Date;
	durationMs?: number | null;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse interface definitions JSON string.
 *
 * @param interfaceDefinitions - JSON string from JobVersion.interfaceDefinitions
 * @returns Parsed interface definitions or null if invalid
 */
export function parseInterfaceDefinitions(
	interfaceDefinitions: string | null | undefined
): InterfaceDefinitions | null {
	if (!interfaceDefinitions || interfaceDefinitions.trim() === '') {
		return null;
	}

	try {
		const parsed = JSON.parse(interfaceDefinitions);
		return parsed as InterfaceDefinitions;
	} catch (error) {
		console.error('Failed to parse interfaceDefinitions:', error);
		return null;
	}
}

/**
 * Get the input schema of the first task (task_001).
 * This is used for parameter input form generation.
 *
 * @param interfaceDefinitions - JSON string from JobVersion.interfaceDefinitions
 * @returns Input schema for the first task or null if not available
 */
export function getFirstTaskInputSchema(
	interfaceDefinitions: string | null | undefined
): JSONSchema | null {
	const definitions = parseInterfaceDefinitions(interfaceDefinitions);

	if (!definitions) {
		return null;
	}

	// Get task IDs sorted alphabetically (task_001, task_002, etc.)
	const taskIds = Object.keys(definitions).sort();

	if (taskIds.length === 0) {
		return null;
	}

	const firstTask = definitions[taskIds[0]];

	if (!firstTask || !firstTask.input_schema) {
		return null;
	}

	return firstTask.input_schema;
}

/**
 * Parse user input schema JSON string.
 * Issue #410: Used to retrieve LLM-generated user input schema.
 *
 * @param userInputSchema - JSON string from JobVersion.userInputSchema
 * @returns Parsed JSON schema or null if invalid/empty
 */
export function parseUserInputSchema(
	userInputSchema: string | null | undefined
): JSONSchema | null {
	if (!userInputSchema || userInputSchema.trim() === '') {
		return null;
	}

	try {
		const parsed = JSON.parse(userInputSchema);
		// Validate it looks like a JSON Schema
		if (parsed && typeof parsed === 'object' && parsed.type === 'object') {
			return parsed as JSONSchema;
		}
		return null;
	} catch (error) {
		console.error('Failed to parse userInputSchema:', error);
		return null;
	}
}

/**
 * Get user input schema with fallback to first task input schema.
 * Issue #410: Prioritizes LLM-generated userInputSchema, falls back to
 * inferring from first task's interface definition.
 *
 * @param userInputSchema - JSON string from JobVersion.userInputSchema (preferred)
 * @param interfaceDefinitions - JSON string from JobVersion.interfaceDefinitions (fallback)
 * @returns Input schema for user input form generation, or null if unavailable
 */
export function getUserInputSchema(
	userInputSchema: string | null | undefined,
	interfaceDefinitions: string | null | undefined
): JSONSchema | null {
	// Issue #410: Prioritize LLM-generated userInputSchema
	const parsedUserInputSchema = parseUserInputSchema(userInputSchema);
	if (parsedUserInputSchema) {
		return parsedUserInputSchema;
	}

	// Fallback to first task input schema for backward compatibility
	return getFirstTaskInputSchema(interfaceDefinitions);
}

/**
 * Merge task details from JobQueue with interface definitions from JobVersion.
 * Creates enriched task progress items for UI display.
 *
 * @param tasks - Task details from JobQueue API
 * @param interfaceDefinitions - JSON string from JobVersion.interfaceDefinitions
 * @returns Enriched task progress items with names and schemas
 */
export function mergeTasksWithInterfaces(
	tasks: TaskDetail[],
	interfaceDefinitions: string | null | undefined
): TaskProgressItem[] {
	const definitions = parseInterfaceDefinitions(interfaceDefinitions) || {};

	return tasks.map((task) => {
		// Generate task ID from order (task_001, task_002, etc.)
		const taskId = `task_${String(task.order).padStart(3, '0')}`;
		const iface = definitions[taskId];

		return {
			taskId,
			taskName: iface?.interface_name || `Task ${task.order}`,
			order: task.order,
			status: task.status,
			inputSchema: iface?.input_schema,
			outputSchema: iface?.output_schema,
			inputData: task.input_data,
			outputData: task.output_data,
			error: task.error,
			startedAt: task.started_at ? new Date(task.started_at) : undefined,
			finishedAt: task.finished_at ? new Date(task.finished_at) : undefined,
			durationMs: task.duration_ms
		};
	});
}

/**
 * Get task name from interface definitions.
 *
 * @param order - Task order (1, 2, 3, etc.)
 * @param interfaceDefinitions - JSON string from JobVersion.interfaceDefinitions
 * @returns Task name from interface or default "Task N"
 */
export function getTaskName(
	order: number,
	interfaceDefinitions: string | null | undefined
): string {
	const definitions = parseInterfaceDefinitions(interfaceDefinitions);

	if (!definitions) {
		return `Task ${order}`;
	}

	const taskId = `task_${String(order).padStart(3, '0')}`;
	const iface = definitions[taskId];

	return iface?.interface_name || `Task ${order}`;
}

/**
 * Convert string parameters to proper types based on JSON Schema.
 * HTML form inputs always return strings, so we need to convert them
 * to the types specified in the schema (integer, number, boolean, etc.)
 *
 * @param params - Record of string parameters from form inputs
 * @param schema - JSON Schema with type definitions
 * @returns Record with properly typed values
 */
export function convertParamsToSchemaTypes(
	params: Record<string, string>,
	schema: JSONSchema | null | undefined
): Record<string, unknown> {
	if (!schema?.properties) {
		// No schema available, return params as-is
		return { ...params };
	}

	const result: Record<string, unknown> = {};

	for (const [key, value] of Object.entries(params)) {
		const propSchema = schema.properties[key];

		if (!propSchema) {
			// Property not in schema, keep as string
			result[key] = value;
			continue;
		}

		// Convert based on schema type
		switch (propSchema.type) {
			case 'integer': {
				const parsed = parseInt(value, 10);
				result[key] = isNaN(parsed) ? value : parsed;
				break;
			}
			case 'number': {
				const parsed = parseFloat(value);
				result[key] = isNaN(parsed) ? value : parsed;
				break;
			}
			case 'boolean': {
				result[key] = value === 'true' || value === '1';
				break;
			}
			case 'array': {
				// Try to parse as JSON array, otherwise split by comma
				try {
					result[key] = JSON.parse(value);
				} catch {
					result[key] = value.split(',').map((s) => s.trim());
				}
				break;
			}
			case 'object': {
				// Try to parse as JSON object
				try {
					result[key] = JSON.parse(value);
				} catch {
					result[key] = value;
				}
				break;
			}
			default:
				// String or unknown type, keep as-is
				result[key] = value;
		}
	}

	return result;
}
