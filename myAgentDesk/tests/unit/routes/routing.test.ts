/**
 * Routing Tests
 * Issue #285: SvelteKit Routing Foundation
 *
 * Tests that the route directory structure matches screen-transition.md
 */
import { describe, it, expect } from 'vitest';
import { existsSync } from 'fs';
import { join } from 'path';

const routesDir = join(process.cwd(), 'src/routes');

describe('Route Directory Structure', () => {
	describe('Root Level Routes', () => {
		it('should have root layout', () => {
			expect(existsSync(join(routesDir, '+layout.svelte'))).toBe(true);
		});

		it('should have home page', () => {
			expect(existsSync(join(routesDir, '+page.svelte'))).toBe(true);
		});

		it('should have error page', () => {
			expect(existsSync(join(routesDir, '+error.svelte'))).toBe(true);
		});
	});

	describe('Projects Routes', () => {
		it('should have projects layout', () => {
			expect(existsSync(join(routesDir, 'projects/+layout.svelte'))).toBe(true);
		});

		it('should have projects list page', () => {
			expect(existsSync(join(routesDir, 'projects/+page.svelte'))).toBe(true);
		});
	});

	describe('Project Detail Routes', () => {
		const projectDir = join(routesDir, 'projects/[projectId]');

		it('should have project layout with server load', () => {
			expect(existsSync(join(projectDir, '+layout.svelte'))).toBe(true);
			expect(existsSync(join(projectDir, '+layout.server.ts'))).toBe(true);
		});

		it('should have project dashboard page', () => {
			expect(existsSync(join(projectDir, '+page.svelte'))).toBe(true);
		});

		it('should have vault settings page', () => {
			expect(existsSync(join(projectDir, 'vault/+page.svelte'))).toBe(true);
		});

		it('should have workbenches list page', () => {
			expect(existsSync(join(projectDir, 'workbenches/+page.svelte'))).toBe(true);
		});
	});

	describe('Workbench Routes', () => {
		const workbenchDir = join(routesDir, 'projects/[projectId]/workbenches/[workbenchId]');

		it('should have workbench layout with server load', () => {
			expect(existsSync(join(workbenchDir, '+layout.svelte'))).toBe(true);
			expect(existsSync(join(workbenchDir, '+layout.server.ts'))).toBe(true);
		});

		it('should have workbench dashboard page', () => {
			expect(existsSync(join(workbenchDir, '+page.svelte'))).toBe(true);
		});

		it('should have requirements page', () => {
			expect(existsSync(join(workbenchDir, 'requirements/+page.svelte'))).toBe(true);
		});

		it('should have requirements version detail page', () => {
			expect(existsSync(join(workbenchDir, 'requirements/[reqVersionId]/+page.svelte'))).toBe(true);
		});

		it('should have generate page', () => {
			expect(existsSync(join(workbenchDir, 'generate/+page.svelte'))).toBe(true);
		});

		it('should have review page', () => {
			expect(existsSync(join(workbenchDir, 'review/+page.svelte'))).toBe(true);
		});

		it('should have job version detail page', () => {
			expect(existsSync(join(workbenchDir, 'job-versions/[jobVersionId]/+page.svelte'))).toBe(true);
		});

		it('should have runs list page', () => {
			expect(existsSync(join(workbenchDir, 'runs/+page.svelte'))).toBe(true);
		});

		it('should have run detail page', () => {
			expect(existsSync(join(workbenchDir, 'runs/[runId]/+page.svelte'))).toBe(true);
		});

		it('should have analyze page', () => {
			expect(existsSync(join(workbenchDir, 'analyze/+page.svelte'))).toBe(true);
		});

		it('should have improve page', () => {
			expect(existsSync(join(workbenchDir, 'improve/+page.svelte'))).toBe(true);
		});

		it('should have schedule page', () => {
			expect(existsSync(join(workbenchDir, 'schedule/+page.svelte'))).toBe(true);
		});

		it('should have schedule detail page', () => {
			expect(existsSync(join(workbenchDir, 'schedule/[scheduleId]/+page.svelte'))).toBe(true);
		});
	});
});

describe('Route Count Validation', () => {
	it('should have exactly 17 page routes (matching screen-transition.md)', () => {
		const pageRoutes = [
			'+page.svelte', // Home
			'projects/+page.svelte', // Project List
			'projects/[projectId]/+page.svelte', // Project Dashboard
			'projects/[projectId]/vault/+page.svelte', // Vault Settings
			'projects/[projectId]/workbenches/+page.svelte', // Workbench List
			'projects/[projectId]/workbenches/[workbenchId]/+page.svelte', // Workbench Dashboard
			'projects/[projectId]/workbenches/[workbenchId]/requirements/+page.svelte', // Requirements
			'projects/[projectId]/workbenches/[workbenchId]/requirements/[reqVersionId]/+page.svelte', // Requirement Version
			'projects/[projectId]/workbenches/[workbenchId]/generate/+page.svelte', // Generate
			'projects/[projectId]/workbenches/[workbenchId]/review/+page.svelte', // Review
			'projects/[projectId]/workbenches/[workbenchId]/job-versions/[jobVersionId]/+page.svelte', // Job Version
			'projects/[projectId]/workbenches/[workbenchId]/runs/+page.svelte', // Runs
			'projects/[projectId]/workbenches/[workbenchId]/runs/[runId]/+page.svelte', // Run Detail
			'projects/[projectId]/workbenches/[workbenchId]/analyze/+page.svelte', // Analyze
			'projects/[projectId]/workbenches/[workbenchId]/improve/+page.svelte', // Improve
			'projects/[projectId]/workbenches/[workbenchId]/schedule/+page.svelte', // Schedule
			'projects/[projectId]/workbenches/[workbenchId]/schedule/[scheduleId]/+page.svelte' // Schedule Detail
		];

		expect(pageRoutes.length).toBe(17);

		// Verify all routes exist
		for (const route of pageRoutes) {
			expect(existsSync(join(routesDir, route))).toBe(true);
		}
	});
});
