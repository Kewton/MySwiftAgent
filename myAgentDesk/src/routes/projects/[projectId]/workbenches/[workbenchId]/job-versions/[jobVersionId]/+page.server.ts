/**
 * JobVersion Detail Page Server
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Server-side logic for the JobVersion detail page.
 * Loads job version data including task breakdown, interfaces, and workflows.
 */

import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { jobVersionRepository } from '$lib/server/repositories/job-version';
import { requirementVersionRepository } from '$lib/server/repositories/requirement-version';

/**
 * Task from task breakdown.
 */
export interface TaskBreakdownItem {
	task_id: string;
	name: string;
	description: string;
	recommended_apis: string[];
	inputInterface?: Record<string, unknown> | null;
	outputInterface?: Record<string, unknown> | null;
}

/**
 * Workflow status from workflows JSON.
 */
export interface WorkflowStatusItem {
	task_id: string;
	task_name: string;
	status: string;
	workflow_name: string | null;
	generation_time_ms: number | null;
	langfuse_trace_id: string | null;
	summary?: {
		yaml_preview?: string;
		yaml_content?: string;
		sample_input?: Record<string, unknown>;
		test_result?: Record<string, unknown>;
	} | null;
}

/**
 * Job version detail data for the page.
 */
export interface JobVersionDetailData {
	id: string;
	workbenchId: string;
	versionLabel: string;
	status: string;
	majorVersion: number;
	minorVersion: number;
	sourceRequirementVersion: {
		id: string;
		version: number;
	};
	externalTraceId: string | null;
	generatedAt: string | null;
	createdAt: string;
	tasks: TaskBreakdownItem[];
	interfaceDefinitions: {
		inputSchema: Record<string, unknown> | null;
		outputSchema: Record<string, unknown> | null;
	};
	workflows: WorkflowStatusItem[];
}

/**
 * Load function for the JobVersion detail page.
 * Validates ownership and returns parsed job version data.
 */
export const load: PageServerLoad = async ({ params, parent }) => {
	const { workbenchId, jobVersionId } = params;

	// Get parent data (includes workbench validation)
	await parent();

	// Fetch job version
	const jv = await jobVersionRepository.findById(jobVersionId);

	// Check if exists
	if (!jv) {
		throw error(404, {
			message: 'Job version not found'
		});
	}

	// Ownership guard: verify job version belongs to this workbench
	if (jv.workbenchId !== workbenchId) {
		throw error(404, {
			message: 'Job version not found'
		});
	}

	// Get source requirement version
	const reqVersion = await requirementVersionRepository.findById(jv.sourceRequirementVersionId);

	// Parse task breakdown
	let tasks: TaskBreakdownItem[] = [];
	if (jv.taskBreakdown) {
		try {
			const parsed = JSON.parse(jv.taskBreakdown);
			// Support both formats: { tasks: [...] } and [...]
			const rawTasks = Array.isArray(parsed) ? parsed : parsed.tasks || [];
			// Normalize task_id field (support both 'id' and 'task_id')
			tasks = rawTasks.map((t: Record<string, unknown>) => ({
				task_id: (t.task_id || t.id || '') as string,
				name: (t.name || '') as string,
				description: (t.description || '') as string,
				recommended_apis: (t.recommended_apis || []) as string[],
				inputInterface: t.inputInterface as Record<string, unknown> | null,
				outputInterface: t.outputInterface as Record<string, unknown> | null
			}));
		} catch {
			console.error('Failed to parse task breakdown');
		}
	}

	// Parse interface definitions (per-task format from Issue #310)
	// Format: { task_001: { input_schema: {...}, output_schema: {...} }, task_002: {...} }
	let interfaceDefinitions = {
		inputSchema: null as Record<string, unknown> | null,
		outputSchema: null as Record<string, unknown> | null
	};
	let interfacesByTask: Record<
		string,
		{ input_schema: Record<string, unknown> | null; output_schema: Record<string, unknown> | null }
	> = {};

	if (jv.interfaceDefinitions) {
		try {
			const parsed = JSON.parse(jv.interfaceDefinitions);

			// Check if it's per-task format (keys are task IDs like task_001, task_002)
			const isPerTaskFormat =
				typeof parsed === 'object' &&
				parsed !== null &&
				Object.keys(parsed).some((key) => key.startsWith('task_'));

			if (isPerTaskFormat) {
				// Per-task format from Issue #310
				interfacesByTask = parsed;

				// Extract first task's interface for the combined view
				const firstTaskKey = Object.keys(parsed)[0];
				if (firstTaskKey && parsed[firstTaskKey]) {
					const firstTask = parsed[firstTaskKey];
					interfaceDefinitions = {
						inputSchema: firstTask.input_schema || null,
						outputSchema: firstTask.output_schema || null
					};
				}
			} else {
				// Legacy format: { inputSchema/outputSchema } or { input/output }
				interfaceDefinitions = {
					inputSchema: parsed.inputSchema || parsed.input || null,
					outputSchema: parsed.outputSchema || parsed.output || null
				};
			}
		} catch {
			console.error('Failed to parse interface definitions');
		}
	}

	// Merge interface definitions into tasks
	if (Object.keys(interfacesByTask).length > 0) {
		tasks = tasks.map((task) => {
			const taskInterface = interfacesByTask[task.task_id];
			if (taskInterface) {
				return {
					...task,
					inputInterface: taskInterface.input_schema || null,
					outputInterface: taskInterface.output_schema || null
				};
			}
			return task;
		});
	}

	// Parse workflows
	let workflows: WorkflowStatusItem[] = [];
	if (jv.workflows) {
		try {
			const parsed = JSON.parse(jv.workflows);
			// Support both formats: { workflow_statuses: [...] } and [...]
			const rawWorkflows = Array.isArray(parsed) ? parsed : parsed.workflow_statuses || [];
			// Normalize workflow fields
			workflows = rawWorkflows.map((w: Record<string, unknown>) => ({
				task_id: (w.task_id || w.id || '') as string,
				task_name: (w.task_name || w.name || '') as string,
				status: (w.status || 'pending') as string,
				workflow_name: (w.workflow_name || null) as string | null,
				generation_time_ms: (w.generation_time_ms || null) as number | null,
				langfuse_trace_id: (w.langfuse_trace_id || null) as string | null,
				summary: w.summary as WorkflowStatusItem['summary']
			}));
		} catch {
			console.error('Failed to parse workflows');
		}
	}

	const jobVersionDetail: JobVersionDetailData = {
		id: jv.id,
		workbenchId: jv.workbenchId,
		versionLabel: jv.versionLabel,
		status: jv.status,
		majorVersion: jv.majorVersion,
		minorVersion: jv.minorVersion,
		sourceRequirementVersion: {
			id: jv.sourceRequirementVersionId,
			version: reqVersion?.version ?? jv.majorVersion
		},
		externalTraceId: jv.externalTraceId,
		generatedAt: jv.generatedAt?.toISOString() ?? null,
		createdAt: jv.createdAt.toISOString(),
		tasks,
		interfaceDefinitions,
		workflows
	};

	return {
		jobVersion: jobVersionDetail
	};
};
