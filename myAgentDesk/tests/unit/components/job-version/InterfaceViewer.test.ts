/**
 * InterfaceViewer Component Tests
 * Issue #292: Review Page (JobVersion Detail)
 *
 * Tests for the interface viewer component that displays JSON Schema.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/svelte';
import InterfaceViewer from '$lib/components/job-version/InterfaceViewer.svelte';

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

describe('InterfaceViewer Component', () => {
	const createSchema = (overrides = {}) => ({
		type: 'object',
		properties: {
			userId: {
				type: 'string',
				description: 'The unique identifier for the user'
			},
			email: {
				type: 'string',
				format: 'email'
			},
			age: {
				type: 'integer',
				minimum: 0
			}
		},
		required: ['userId', 'email'],
		...overrides
	});

	describe('Basic Rendering', () => {
		it('should render title', () => {
			const schema = createSchema();
			render(InterfaceViewer, { props: { schema, title: 'Input Interface' } });

			expect(screen.getByText('Input Interface')).toBeDefined();
		});

		it('should render formatted JSON', () => {
			const schema = createSchema();
			const { container } = render(InterfaceViewer, {
				props: { schema, title: 'Input Interface' }
			});

			// Should have pre element for formatted code
			const preElement = container.querySelector('pre');
			expect(preElement).not.toBeNull();
		});

		it('should format JSON with proper indentation', () => {
			const schema = createSchema();
			const { container } = render(InterfaceViewer, {
				props: { schema, title: 'Input Interface' }
			});

			const preElement = container.querySelector('pre');
			const content = preElement?.textContent || '';

			// Should contain the schema properties
			expect(content).toContain('userId');
			expect(content).toContain('email');
			expect(content).toContain('type');
		});

		it('should display "type" field from schema', () => {
			const schema = createSchema();
			const { container } = render(InterfaceViewer, {
				props: { schema, title: 'Input Interface' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('"type"');
			expect(content).toContain('"object"');
		});
	});

	describe('Copy Functionality', () => {
		it('should have copy button', () => {
			const schema = createSchema();
			render(InterfaceViewer, { props: { schema, title: 'Input Interface' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			expect(copyButton).toBeDefined();
		});

		it('should copy content to clipboard when copy button is clicked', async () => {
			const schema = createSchema();
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			Object.assign(navigator, {
				clipboard: {
					writeText: writeTextMock
				}
			});

			render(InterfaceViewer, { props: { schema, title: 'Input Interface' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			await fireEvent.click(copyButton);

			expect(writeTextMock).toHaveBeenCalled();
		});

		it('should show success feedback after copy', async () => {
			const schema = createSchema();
			const writeTextMock = vi.fn().mockResolvedValue(undefined);
			Object.assign(navigator, {
				clipboard: {
					writeText: writeTextMock
				}
			});

			render(InterfaceViewer, { props: { schema, title: 'Input Interface' } });

			const copyButton = screen.getByRole('button', { name: /copy/i });
			await fireEvent.click(copyButton);

			// Should show "Copied!" or similar feedback
			expect(screen.getByText(/copied/i)).toBeDefined();
		});
	});

	describe('Syntax Highlighting', () => {
		it('should apply syntax highlighting class', () => {
			const schema = createSchema();
			const { container } = render(InterfaceViewer, {
				props: { schema, title: 'Input Interface' }
			});

			// Should have syntax highlighting container
			const codeElement = container.querySelector('code');
			expect(codeElement?.className).toContain('json');
		});
	});

	describe('Edge Cases', () => {
		it('should handle null schema', () => {
			render(InterfaceViewer, { props: { schema: null, title: 'Input Interface' } });

			// Should render without errors, possibly show empty state
			expect(screen.getByText('Input Interface')).toBeDefined();
		});

		it('should handle empty object schema', () => {
			render(InterfaceViewer, { props: { schema: {}, title: 'Input Interface' } });

			const { container } = render(InterfaceViewer, {
				props: { schema: {}, title: 'Empty Schema' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('{}');
		});

		it('should handle deeply nested schema', () => {
			const deepSchema = {
				type: 'object',
				properties: {
					level1: {
						type: 'object',
						properties: {
							level2: {
								type: 'object',
								properties: {
									level3: { type: 'string' }
								}
							}
						}
					}
				}
			};

			const { container } = render(InterfaceViewer, {
				props: { schema: deepSchema, title: 'Deep Schema' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('level1');
			expect(content).toContain('level2');
			expect(content).toContain('level3');
		});

		it('should handle array type schema', () => {
			const arraySchema = {
				type: 'array',
				items: {
					type: 'object',
					properties: {
						id: { type: 'string' }
					}
				}
			};

			const { container } = render(InterfaceViewer, {
				props: { schema: arraySchema, title: 'Array Schema' }
			});

			const content = container.querySelector('pre')?.textContent || '';
			expect(content).toContain('array');
			expect(content).toContain('items');
		});
	});

	describe('Accessibility', () => {
		it('should have accessible structure', () => {
			const schema = createSchema();
			const { container } = render(InterfaceViewer, {
				props: { schema, title: 'Input Interface' }
			});

			// Should have semantic elements
			expect(container.querySelector('h3, h4, h5')).not.toBeNull();
		});

		it('should have accessible copy button', () => {
			const schema = createSchema();
			render(InterfaceViewer, { props: { schema, title: 'Input Interface' } });

			const button = screen.getByRole('button', { name: /copy/i });
			expect(button.getAttribute('aria-label') || button.textContent).toBeTruthy();
		});
	});
});
