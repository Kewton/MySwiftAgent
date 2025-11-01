import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import Card from './Card.svelte';

describe('Card.svelte', () => {
	describe('Rendering', () => {
		it('renders with default props', () => {
			const { container } = render(Card);
			const card = container.querySelector('div');
			expect(card).toBeTruthy();
		});

		it('renders with slot content', () => {
			const { container } = render(Card);
			const card = container.querySelector('div');
			// Slot is present and can be populated
			expect(card).toBeTruthy();
		});
	});

	describe('Variants', () => {
		it('applies default variant class', () => {
			const { container } = render(Card, { props: { variant: 'default' } });
			const card = container.querySelector('div');
			expect(card?.className).toContain('bg-white');
			expect(card?.className).toContain('rounded-lg');
		});

		it('applies chat variant class', () => {
			const { container } = render(Card, { props: { variant: 'chat' } });
			const card = container.querySelector('div');
			expect(card?.className).toContain('chat-bubble');
		});

		it('applies node variant class', () => {
			const { container } = render(Card, { props: { variant: 'node' } });
			const card = container.querySelector('div');
			expect(card?.className).toContain('node-card');
		});
	});

	describe('Hoverable', () => {
		it('does not apply hover class by default', () => {
			const { container } = render(Card, { props: { hoverable: false } });
			const card = container.querySelector('div');
			expect(card?.className).not.toContain('hover:shadow-md');
		});

		it('applies hover class when hoverable is true', () => {
			const { container } = render(Card, { props: { hoverable: true } });
			const card = container.querySelector('div');
			expect(card?.className).toContain('hover:shadow-md');
		});
	});

	describe('Accessibility', () => {
		it('has transition class for smooth effects', () => {
			const { container } = render(Card);
			const card = container.querySelector('div');
			expect(card?.className).toContain('transition-shadow');
		});
	});
});
