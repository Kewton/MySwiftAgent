/**
 * Workbench Guard Tests
 * Issue #285: SvelteKit Routing Foundation
 */
import { describe, it, expect } from 'vitest';
import { validateWorkbenchAccess, type Workbench } from '$lib/guards/workbench-guard';

describe('Workbench Guard', () => {
	describe('validateWorkbenchAccess', () => {
		it('should return workbench when it exists and belongs to project', () => {
			const mockWorkbench: Workbench = {
				id: 'wb_abc123',
				name: 'Test Workbench',
				projectId: 'proj_001'
			};
			const result = validateWorkbenchAccess(mockWorkbench, 'wb_abc123', 'proj_001');

			expect(result.valid).toBe(true);
			expect(result.workbench).toEqual(mockWorkbench);
		});

		it('should return error when workbench is null', () => {
			const result = validateWorkbenchAccess(null, 'wb_abc123', 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('WORKBENCH_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});

		it('should return error when workbench is undefined', () => {
			const result = validateWorkbenchAccess(undefined, 'wb_abc123', 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('WORKBENCH_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});

		it('should return error when workbench ID does not match', () => {
			const mockWorkbench: Workbench = {
				id: 'wb_other',
				name: 'Other Workbench',
				projectId: 'proj_001'
			};
			const result = validateWorkbenchAccess(mockWorkbench, 'wb_abc123', 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('WORKBENCH_NOT_FOUND');
			expect(result.error?.status).toBe(404);
		});

		it('should return error when workbench belongs to different project (security)', () => {
			const mockWorkbench: Workbench = {
				id: 'wb_abc123',
				name: 'Test Workbench',
				projectId: 'proj_002' // Different project
			};
			const result = validateWorkbenchAccess(mockWorkbench, 'wb_abc123', 'proj_001');

			expect(result.valid).toBe(false);
			expect(result.error?.code).toBe('WORKBENCH_NOT_FOUND');
			expect(result.error?.status).toBe(404);
			// Security: Should NOT reveal that workbench exists in another project
		});
	});
});
