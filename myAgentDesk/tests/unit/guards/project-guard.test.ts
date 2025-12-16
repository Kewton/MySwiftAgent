/**
 * Project Guard Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect } from 'vitest';
import { validateProjectAccess, type Project } from '$lib/guards/project-guard';

describe('Project Guard', () => {
	describe('validateProjectAccess', () => {
		it('should return project when project exists', () => {
			const mockProject: Project = { id: 'proj_001', name: 'Test Project' };
			const result = validateProjectAccess(mockProject, 'proj_001');

			expect(result.valid).toBe(true);
			expect(result.project).toEqual(mockProject);
		});

		it('should return error when project is null', () => {
			const result = validateProjectAccess(null, 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('PROJECT_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});

		it('should return error when project is undefined', () => {
			const result = validateProjectAccess(undefined, 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('PROJECT_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});

		it('should return error when project ID does not match', () => {
			const mockProject: Project = { id: 'proj_002', name: 'Other Project' };
			const result = validateProjectAccess(mockProject, 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('PROJECT_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});
	});
});
