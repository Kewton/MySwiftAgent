/**
 * WorkflowViewer Component Tests
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Tests for the workflow viewer component that displays YAML with syntax highlighting.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/svelte';
import WorkflowViewer from '$lib/components/job-version/WorkflowViewer.svelte';

// Mock $app/stores
vi.mock('$app/stores', () => ({
	page: {
		subscribe: vi.fn((fn) => {
			fn({
				url: { pathname: '/projects/proj_001/workbenches/wb_001/job-versions/jv_001' }
			});
			return () => {};
		})
	}
}));

describe('WorkflowViewer Component', () => {
	const createWorkflowYaml = () => `version: 0.5
nodes:
  source:
    agent: fetchAgent
    params:
      url: /api/users
      method: GET
  transform:
    agent: transformAgent
    inputs:
      - source
    params:
      template: "{{ source.data }}"
  output:
    agent: copyAgent
    inputs:
      - transform
`;

	describe('Basic Rendering', () => {
		it('should render workflow title', () => {
			const yaml = createWorkflowYaml();
			render(WorkflowViewer, { props: { yaml, title: 'Generated Workflow' } });

			expect(screen.getByText('Generated Workflow')).toBeDefined();
		});

		it('should render YAML content', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow' }
			});

			const preElement = container.querySelector('pre');
			expect(preElement).not.toBeNull();
			expect(preElement?.textContent).toContain('version: 0.5');
		});

		it('should preserve YAML formatting', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('nodes:');
			expect(content).toContain('source:');
			expect(content).toContain('agent: fetchAgent');
		});
	});

	describe('Syntax Highlighting', () => {
		it('should apply YAML syntax highlighting class', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow' }
			});

			const codeElement = container.querySelector('code');
			expect(codeElement?.className).toContain('yaml');
		});

		it('should highlight keywords', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow' }
			});

			// With highlight.js, there should be span elements with highlighting
			const highlightedSpans = container.querySelectorAll('code span');
			expect(highlightedSpans.length).toBeGreaterThan(0);
		});
	});

	describe('Copy Functionality', () => {
		it('should have copy button', () => {
			const yaml = createWorkflowYaml();
			render(WorkflowViewer, { props: { yaml, title: 'Generated Workflow' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			expect(copyButton).toBeDefined();
		});

		it('should copy YAML to clipboard when clicked', async () => {
			const yaml = createWorkflowYaml();
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			Object.assign(navigator, {
				clipboard: {
					writeText: writeTextMock
				}
			});

			render(WorkflowViewer, { props: { yaml, title: 'Generated Workflow' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			await fireEvent.click(copyButton);

			expect(writeTextMock).toHaveBeenCalledWith(yaml);
		});

		it('should show success feedback after copy', async () => {
			const yaml = createWorkflowYaml();
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			Object.assign(navigator, {
				clipboard: {
					writeText: writeTextMock
				}
			});

			render(WorkflowViewer, { props: { yaml, title: 'Generated Workflow' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			await fireEvent.click(copyButton);

			expect(screen.getByText(/copied/i)).toBeDefined();
		});
	});

	describe('Collapsible Functionality', () => {
		it('should have collapse/expand button when collapsible is true', () => {
			const yaml = createWorkflowYaml();
			render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow', collapsible: true }
			});

			const toggleButton = screen.getByRole('button', { name: /collapse|expand|show|hide/i });
			expect(toggleButton).toBeDefined();
		});

		it('should show content when not collapsed', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow', collapsible: true, collapsed: false }
			});

			// Content should be visible - check pre element contains the content
			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('version: 0.5');
		});

		it('should hide content when collapsed', () => {
			const yaml = createWorkflowYaml();
			render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow', collapsible: true, collapsed: true }
			});

			// Content should be hidden
			expect(screen.queryByText(/agent: fetchAgent/)).toBeNull();
			// But header should still be visible
			expect(screen.getByText('Generated Workflow')).toBeDefined();
		});

		it('should toggle state when button is clicked', async () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow', collapsible: true, collapsed: false }
			});

			// Content should be visible initially
			expect(container.querySelector('.content')).not.toBeNull();

			const toggleButton = screen.getByRole('button', { name: /collapse|hide/i });
			await fireEvent.click(toggleButton);

			// After click, the button text should change
			await waitFor(() => {
				expect(screen.getByRole('button', { name: /expand|show/i })).toBeDefined();
			});
		});
	});

	describe('Edge Cases', () => {
		it('should handle empty YAML', () => {
			render(WorkflowViewer, { props: { yaml: '', title: 'Empty Workflow' } });

			expect(screen.getByText('Empty Workflow')).toBeDefined();
		});

		it('should handle null YAML', () => {
			render(WorkflowViewer, { props: { yaml: null, title: 'No Workflow' } });

			expect(screen.getByText('No Workflow')).toBeDefined();
		});

		it('should handle complex nested YAML', () => {
			const complexYaml = `version: 0.5
nodes:
  source:
    agent: fetchAgent
    params:
      headers:
        Authorization: Bearer token
        Content-Type: application/json
      body:
        items:
          - id: 1
            name: Item 1
          - id: 2
            name: Item 2
`;
			const { container } = render(WorkflowViewer, {
				props: { yaml: complexYaml, title: 'Complex Workflow' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('Authorization');
			expect(content).toContain('Item 1');
		});

		it('should handle very long YAML', () => {
			const longYaml = Array.from(
				{ length: 100 },
				(_, i) => `node_${i}:\n  agent: agent${i}\n`
			).join('');

			const { container } = render(WorkflowViewer, {
				props: { yaml: longYaml, title: 'Long Workflow' }
			});

			const preElement = container.querySelector('pre');
			expect(preElement).not.toBeNull();
		});
	});

	describe('Line Numbers', () => {
		it('should display line numbers when showLineNumbers is true', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Workflow', showLineNumbers: true }
			});

			// Should have line number elements
			const lineNumbers = container.querySelectorAll('.line-number');
			expect(lineNumbers.length).toBeGreaterThan(0);
		});
	});

	describe('Accessibility', () => {
		it('should have proper semantic structure', () => {
			const yaml = createWorkflowYaml();
			const { container } = render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow' }
			});

			expect(container.querySelector('pre')).not.toBeNull();
			expect(container.querySelector('code')).not.toBeNull();
		});

		it('should have accessible buttons', () => {
			const yaml = createWorkflowYaml();
			render(WorkflowViewer, {
				props: { yaml, title: 'Generated Workflow', collapsible: true }
			});

			const buttons = screen.getAllByRole('button');
			buttons.forEach((button) => {
				expect(button.getAttribute('aria-label') || button.textContent).toBeTruthy();
			});
		});
	});
});
