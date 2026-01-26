/**
 * Interface Schema Helper Tests
 * Issue #293: JobQueue Integration for Runs
 * Issue #410: Added tests for getUserInputSchema and parseUserInputSchema
 *
 * Tests for interface schema parsing and task progress merging
 */

import { describe, it, expect } from 'vitest';
import {
	getFirstTaskInputSchema,
	parseInterfaceDefinitions,
	mergeTasksWithInterfaces,
	parseUserInputSchema,
	getUserInputSchema,
	type InterfaceDefinitions,
	type TaskInterface,
	type JSONSchema,
	type TaskProgressItem
} from '$lib/utils/interface-schema';
import type { TaskDetail } from '$lib/api/clients/job-queue';

describe('Interface Schema Helpers', () => {
	// Sample interface definitions from JobVersion
	const sampleInterfaceDefinitions: InterfaceDefinitions = {
		task_001: {
			interface_master_id: 'if_01KDD4YJ296FG1TXZDZSWRASWB',
			input_interface_id: 'if_input_001',
			output_interface_id: 'if_output_001',
			interface_name: 'google_search_financials_interface',
			input_schema: {
				type: 'object',
				properties: {
					company_name: { type: 'string', description: 'Company name to search' },
					target_years: { type: 'string', description: 'Target years range' },
					document_types: { type: 'string', description: 'Types of documents' }
				},
				required: ['company_name', 'target_years', 'document_types']
			},
			output_schema: {
				type: 'object',
				properties: {
					success: { type: 'boolean' },
					documents: { type: 'array' }
				}
			}
		},
		task_002: {
			interface_master_id: 'if_02KDD4YJ296FG1TXZDZSWRASWB',
			input_interface_id: 'if_input_002',
			output_interface_id: 'if_output_002',
			interface_name: 'file_reader_pdf_interface',
			input_schema: {
				type: 'object',
				properties: {
					file_path: { type: 'string' }
				},
				required: ['file_path']
			},
			output_schema: {
				type: 'object',
				properties: {
					content: { type: 'string' }
				}
			}
		}
	};

	describe('parseInterfaceDefinitions', () => {
		it('should parse valid JSON interface definitions', () => {
			const jsonString = JSON.stringify(sampleInterfaceDefinitions);
			const result = parseInterfaceDefinitions(jsonString);

			expect(result).not.toBeNull();
			expect(result?.task_001.interface_name).toBe('google_search_financials_interface');
			expect(result?.task_002.interface_name).toBe('file_reader_pdf_interface');
		});

		it('should return null for null input', () => {
			const result = parseInterfaceDefinitions(null);
			expect(result).toBeNull();
		});

		it('should return null for empty string', () => {
			const result = parseInterfaceDefinitions('');
			expect(result).toBeNull();
		});

		it('should return null for invalid JSON', () => {
			const result = parseInterfaceDefinitions('{ invalid json }');
			expect(result).toBeNull();
		});
	});

	describe('getFirstTaskInputSchema', () => {
		it('should return the input schema of the first task (task_001)', () => {
			const jsonString = JSON.stringify(sampleInterfaceDefinitions);
			const result = getFirstTaskInputSchema(jsonString);

			expect(result).not.toBeNull();
			expect(result?.type).toBe('object');
			expect(result?.properties?.company_name).toBeDefined();
			expect(result?.properties?.target_years).toBeDefined();
			expect(result?.required).toContain('company_name');
		});

		it('should return null when no interface definitions', () => {
			const result = getFirstTaskInputSchema(null);
			expect(result).toBeNull();
		});

		it('should return null for empty interface definitions', () => {
			const result = getFirstTaskInputSchema(JSON.stringify({}));
			expect(result).toBeNull();
		});

		it('should handle task_001 without input_schema', () => {
			const incomplete: InterfaceDefinitions = {
				task_001: {
					interface_master_id: 'if_01',
					input_interface_id: 'if_input_01',
					output_interface_id: 'if_output_01',
					interface_name: 'test_interface'
					// Missing input_schema and output_schema
				} as TaskInterface
			};
			const result = getFirstTaskInputSchema(JSON.stringify(incomplete));
			expect(result).toBeNull();
		});
	});

	describe('mergeTasksWithInterfaces', () => {
		const sampleTasks: TaskDetail[] = [
			{
				id: 'task_abc123',
				job_id: 'job_xyz',
				master_id: 'tm_001',
				master_version: 1,
				order: 1,
				status: 'succeeded',
				input_data: { company_name: 'Toyota', target_years: '2020-2024', document_types: 'Annual' },
				output_data: { success: true, documents: ['doc1.pdf', 'doc2.pdf'] },
				attempt: 1,
				error: null,
				started_at: '2024-12-26T10:00:00Z',
				finished_at: '2024-12-26T10:00:12Z',
				duration_ms: 12000,
				created_at: '2024-12-26T10:00:00Z',
				updated_at: '2024-12-26T10:00:12Z'
			},
			{
				id: 'task_def456',
				job_id: 'job_xyz',
				master_id: 'tm_002',
				master_version: 1,
				order: 2,
				status: 'running',
				input_data: { file_path: '/tmp/doc1.pdf' },
				output_data: null,
				attempt: 1,
				error: null,
				started_at: '2024-12-26T10:00:12Z',
				finished_at: null,
				duration_ms: null,
				created_at: '2024-12-26T10:00:12Z',
				updated_at: '2024-12-26T10:00:15Z'
			}
		];

		it('should merge task details with interface definitions', () => {
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);
			const result = mergeTasksWithInterfaces(sampleTasks, interfaceDefString);

			expect(result).toHaveLength(2);

			// First task
			expect(result[0].taskId).toBe('task_001');
			expect(result[0].taskName).toBe('google_search_financials_interface');
			expect(result[0].order).toBe(1);
			expect(result[0].status).toBe('succeeded');
			expect(result[0].inputData).toEqual({
				company_name: 'Toyota',
				target_years: '2020-2024',
				document_types: 'Annual'
			});
			expect(result[0].outputData).toEqual({
				success: true,
				documents: ['doc1.pdf', 'doc2.pdf']
			});
			expect(result[0].inputSchema).toBeDefined();
			expect(result[0].outputSchema).toBeDefined();
			expect(result[0].durationMs).toBe(12000);

			// Second task
			expect(result[1].taskId).toBe('task_002');
			expect(result[1].taskName).toBe('file_reader_pdf_interface');
			expect(result[1].order).toBe(2);
			expect(result[1].status).toBe('running');
			expect(result[1].outputData).toBeNull();
		});

		it('should use default task name when interface not found', () => {
			const tasksWithUnknownOrder: TaskDetail[] = [
				{
					...sampleTasks[0],
					order: 99 // No matching interface
				}
			];

			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);
			const result = mergeTasksWithInterfaces(tasksWithUnknownOrder, interfaceDefString);

			expect(result[0].taskName).toBe('Task 99');
			expect(result[0].inputSchema).toBeUndefined();
		});

		it('should handle null interface definitions', () => {
			const result = mergeTasksWithInterfaces(sampleTasks, null);

			expect(result).toHaveLength(2);
			expect(result[0].taskName).toBe('Task 1');
			expect(result[1].taskName).toBe('Task 2');
		});

		it('should parse date strings into Date objects', () => {
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);
			const result = mergeTasksWithInterfaces(sampleTasks, interfaceDefString);

			expect(result[0].startedAt).toBeInstanceOf(Date);
			expect(result[0].finishedAt).toBeInstanceOf(Date);
			expect(result[1].startedAt).toBeInstanceOf(Date);
			expect(result[1].finishedAt).toBeUndefined();
		});

		it('should include error information for failed tasks', () => {
			const failedTask: TaskDetail[] = [
				{
					...sampleTasks[0],
					status: 'failed',
					error: 'API rate limit exceeded'
				}
			];

			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);
			const result = mergeTasksWithInterfaces(failedTask, interfaceDefString);

			expect(result[0].status).toBe('failed');
			expect(result[0].error).toBe('API rate limit exceeded');
		});
	});

	/**
	 * Issue #410: Tests for parseUserInputSchema
	 */
	describe('parseUserInputSchema', () => {
		it('should parse valid user input schema JSON', () => {
			const schema: JSONSchema = {
				type: 'object',
				properties: {
					keyword: { type: 'string', description: 'Search keyword' },
					email: { type: 'string', description: 'Notification email' }
				},
				required: ['keyword', 'email']
			};
			const jsonString = JSON.stringify(schema);
			const result = parseUserInputSchema(jsonString);

			expect(result).not.toBeNull();
			expect(result?.type).toBe('object');
			expect(result?.properties?.keyword).toBeDefined();
			expect(result?.properties?.email).toBeDefined();
		});

		it('should return null for null input', () => {
			const result = parseUserInputSchema(null);
			expect(result).toBeNull();
		});

		it('should return null for empty string', () => {
			const result = parseUserInputSchema('');
			expect(result).toBeNull();
		});

		it('should return null for whitespace-only string', () => {
			const result = parseUserInputSchema('   ');
			expect(result).toBeNull();
		});

		it('should return null for invalid JSON', () => {
			const result = parseUserInputSchema('{ invalid json }');
			expect(result).toBeNull();
		});

		it('should return null for non-object schema', () => {
			const result = parseUserInputSchema(JSON.stringify({ type: 'string' }));
			expect(result).toBeNull();
		});
	});

	/**
	 * Issue #410: Tests for getUserInputSchema
	 */
	describe('getUserInputSchema', () => {
		const userInputSchema: JSONSchema = {
			type: 'object',
			properties: {
				keyword: { type: 'string', description: 'Search keyword' },
				email: { type: 'string', description: 'Notification email' }
			},
			required: ['keyword', 'email']
		};

		it('should prioritize userInputSchema over interfaceDefinitions', () => {
			const userInputSchemaString = JSON.stringify(userInputSchema);
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);

			const result = getUserInputSchema(userInputSchemaString, interfaceDefString);

			expect(result).not.toBeNull();
			// Should have keyword and email from userInputSchema, not company_name from interface
			expect(result?.properties?.keyword).toBeDefined();
			expect(result?.properties?.email).toBeDefined();
			expect(result?.properties?.company_name).toBeUndefined();
		});

		it('should fall back to interfaceDefinitions when userInputSchema is null', () => {
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);

			const result = getUserInputSchema(null, interfaceDefString);

			expect(result).not.toBeNull();
			// Should have company_name from first task interface
			expect(result?.properties?.company_name).toBeDefined();
			expect(result?.properties?.target_years).toBeDefined();
		});

		it('should fall back to interfaceDefinitions when userInputSchema is empty', () => {
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);

			const result = getUserInputSchema('', interfaceDefString);

			expect(result).not.toBeNull();
			expect(result?.properties?.company_name).toBeDefined();
		});

		it('should fall back to interfaceDefinitions when userInputSchema is invalid', () => {
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);

			const result = getUserInputSchema('{ invalid json }', interfaceDefString);

			expect(result).not.toBeNull();
			expect(result?.properties?.company_name).toBeDefined();
		});

		it('should return null when both userInputSchema and interfaceDefinitions are null', () => {
			const result = getUserInputSchema(null, null);
			expect(result).toBeNull();
		});

		it('should return null when both userInputSchema and interfaceDefinitions are empty', () => {
			const result = getUserInputSchema('', '{}');
			expect(result).toBeNull();
		});

		it('should handle backward compatibility with only interfaceDefinitions', () => {
			// This tests the scenario where userInputSchema is not yet populated (existing data)
			const interfaceDefString = JSON.stringify(sampleInterfaceDefinitions);

			const result = getUserInputSchema(undefined, interfaceDefString);

			expect(result).not.toBeNull();
			expect(result?.properties?.company_name).toBeDefined();
		});
	});
});
