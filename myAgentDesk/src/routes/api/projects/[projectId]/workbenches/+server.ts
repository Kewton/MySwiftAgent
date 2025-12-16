/**
 * Workbench API Endpoints
 * Issue #289: Workbench List/Detail Screens
 *
 * GET  /api/projects/:projectId/workbenches - List workbenches with stats
 * POST /api/projects/:projectId/workbenches - Create a new workbench
 */
import { json, error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { workbenchRepository } from '$lib/server/repositories/workbench';
import type { WorkbenchStatusFilter } from '$lib/types/workbench';

/**
 * GET /api/projects/:projectId/workbenches
 *
 * Returns a list of workbenches for the specified project with stats.
 * Supports filtering by status via query parameter.
 *
 * Query params:
 *   - status: 'all' | 'active' | 'draft' | 'archived' (default: 'all')
 *
 * Response: {
 *   workbenches: WorkbenchListItem[],
 *   statusCounts: WorkbenchStatusCounts,
 *   currentFilter: WorkbenchStatusFilter
 * }
 */
export const GET: RequestHandler = async ({ params, url }) => {
	const { projectId } = params;

	// Validate projectId
	if (!projectId) {
		throw error(400, { message: 'Project ID is required' });
	}

	// Get filter from URL query params
	const statusFilter = (url.searchParams.get('status') as WorkbenchStatusFilter) || 'all';

	// Validate status filter
	const validStatuses = ['all', 'active', 'draft', 'archived'];
	if (!validStatuses.includes(statusFilter)) {
		throw error(400, { message: `Invalid status filter: ${statusFilter}` });
	}

	// Fetch workbenches with stats
	const allWorkbenches = await workbenchRepository.findByProjectWithStats(projectId);

	// Filter by status if not 'all'
	const workbenches =
		statusFilter === 'all'
			? allWorkbenches
			: allWorkbenches.filter((wb) => wb.status === statusFilter);

	// Fetch status counts for filter UI
	const statusCounts = await workbenchRepository.getStatusCounts(projectId);

	return json({
		workbenches,
		statusCounts,
		currentFilter: statusFilter
	});
};

/**
 * POST /api/projects/:projectId/workbenches
 *
 * Creates a new workbench in the specified project.
 *
 * Request body: {
 *   name: string (required),
 *   description?: string
 * }
 *
 * Response: {
 *   workbench: Workbench,
 *   message: string
 * }
 */
export const POST: RequestHandler = async ({ params, request }) => {
	const { projectId } = params;

	// Validate projectId
	if (!projectId) {
		throw error(400, { message: 'Project ID is required' });
	}

	// Parse request body
	let body: { name?: string; description?: string };
	try {
		body = await request.json();
	} catch {
		throw error(400, { message: 'Invalid JSON body' });
	}

	// Validate required fields
	const { name, description } = body;
	if (!name || typeof name !== 'string' || name.trim().length === 0) {
		throw error(400, { message: 'Name is required and must be a non-empty string' });
	}

	// Validate name length
	if (name.trim().length > 100) {
		throw error(400, { message: 'Name must be 100 characters or less' });
	}

	// Validate description if provided
	if (description !== undefined && typeof description !== 'string') {
		throw error(400, { message: 'Description must be a string' });
	}

	if (description && description.length > 500) {
		throw error(400, { message: 'Description must be 500 characters or less' });
	}

	// Create the workbench
	const workbench = await workbenchRepository.create(projectId, name.trim(), description?.trim());

	return json(
		{
			workbench,
			message: 'Workbench created successfully'
		},
		{ status: 201 }
	);
};
