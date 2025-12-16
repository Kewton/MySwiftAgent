/**
 * ProjectCard Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import ProjectCard from '../../../src/lib/components/projects/ProjectCard.svelte';

describe('ProjectCard', () => {
	const mockProject = {
		id: 'proj_001',
		externalProjectId: 'ext_001',
		name: 'Test Project',
		description: 'A test project description',
		lastSyncedAt: null,
		createdAt: new Date('2024-01-01'),
		updatedAt: new Date('2024-01-15'),
		workbenchCount: 3
	};

	it('should render project name', () => {
		render(ProjectCard, { props: { project: mockProject } });
		expect(screen.getByText('Test Project')).toBeTruthy();
	});

	it('should render project description', () => {
		render(ProjectCard, { props: { project: mockProject } });
		expect(screen.getByText('A test project description')).toBeTruthy();
	});

	it('should render workbench count', () => {
		render(ProjectCard, { props: { project: mockProject } });
		expect(screen.getByText(/3/)).toBeTruthy();
	});

	it('should link to project detail page', () => {
		render(ProjectCard, { props: { project: mockProject } });
		const link = screen.getByRole('link');
		expect(link.getAttribute('href')).toBe('/projects/proj_001');
	});

	it('should handle missing description gracefully', () => {
		const projectNoDesc = { ...mockProject, description: null };
		render(ProjectCard, { props: { project: projectNoDesc } });
		expect(screen.getByText('Test Project')).toBeTruthy();
	});

	it('should show zero workbenches correctly', () => {
		const projectNoWorkbenches = { ...mockProject, workbenchCount: 0 };
		render(ProjectCard, { props: { project: projectNoWorkbenches } });
		const countElement = screen.getByLabelText('Workbench count');
		expect(countElement.textContent).toContain('0');
	});
});
