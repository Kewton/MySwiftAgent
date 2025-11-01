import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import AgentCard from './AgentCard.svelte';

describe('AgentCard.svelte', () => {
	describe('Rendering', () => {
		it('renders with required props', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Test Agent',
					description: 'Test description'
				}
			});
			const card = container.querySelector('.node-card');
			expect(card).toBeTruthy();
		});

		it('displays agent name', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Content Generator',
					description: 'Generates content'
				}
			});
			expect(getByText('Content Generator')).toBeTruthy();
		});

		it('displays agent description', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Test Agent',
					description: 'This is a test description'
				}
			});
			expect(getByText('This is a test description')).toBeTruthy();
		});
	});

	describe('Icon', () => {
		it('displays default icon when not provided', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description'
				}
			});
			expect(container.textContent).toContain('🤖');
		});

		it('displays custom icon when provided', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					icon: '✍️'
				}
			});
			expect(container.textContent).toContain('✍️');
		});
	});

	describe('Colors', () => {
		it('applies purple color by default', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description'
				}
			});
			const card = container.querySelector('.node-card');
			expect(card?.className).toContain('border-accent-purple');
		});

		it('applies pink color', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					color: 'pink'
				}
			});
			const card = container.querySelector('.node-card');
			expect(card?.className).toContain('border-accent-pink');
		});

		it('applies orange color', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					color: 'orange'
				}
			});
			const card = container.querySelector('.node-card');
			expect(card?.className).toContain('border-accent-orange');
		});

		it('applies blue color', () => {
			const { container } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					color: 'blue'
				}
			});
			const card = container.querySelector('.node-card');
			expect(card?.className).toContain('border-primary-500');
		});
	});

	describe('Status', () => {
		it('displays active status indicator', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					status: 'active'
				}
			});
			expect(getByText('Active')).toBeTruthy();
		});

		it('displays inactive status indicator', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					status: 'inactive'
				}
			});
			expect(getByText('Inactive')).toBeTruthy();
		});

		it('displays error status indicator', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description',
					status: 'error'
				}
			});
			expect(getByText('Error')).toBeTruthy();
		});
	});

	describe('Buttons', () => {
		it('has Configure button', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description'
				}
			});
			expect(getByText('Configure')).toBeTruthy();
		});

		it('has View Details button', () => {
			const { getByText } = render(AgentCard, {
				props: {
					name: 'Agent',
					description: 'Description'
				}
			});
			expect(getByText('View Details')).toBeTruthy();
		});
	});
});
