import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import Button from './Button.svelte';

describe('Button.svelte', () => {
	describe('Rendering', () => {
		it('renders with default props', () => {
			const { container } = render(Button);
			const button = container.querySelector('button');
			expect(button).toBeTruthy();
		});

		it('has correct button type', () => {
			const { container } = render(Button);
			const button = container.querySelector('button') as HTMLButtonElement;
			expect(button.type).toBe('button');
		});
	});

	describe('Variants', () => {
		it('applies primary variant class', () => {
			const { container } = render(Button, { props: { variant: 'primary' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('bg-primary-500');
		});

		it('applies secondary variant class', () => {
			const { container } = render(Button, { props: { variant: 'secondary' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('bg-gray-200');
		});

		it('applies danger variant class', () => {
			const { container } = render(Button, { props: { variant: 'danger' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('bg-red-500');
		});

		it('applies ghost variant class', () => {
			const { container } = render(Button, { props: { variant: 'ghost' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('bg-transparent');
		});
	});

	describe('Sizes', () => {
		it('applies small size class', () => {
			const { container } = render(Button, { props: { size: 'sm' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('text-sm');
		});

		it('applies medium size class (default)', () => {
			const { container } = render(Button, { props: { size: 'md' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('text-base');
		});

		it('applies large size class', () => {
			const { container } = render(Button, { props: { size: 'lg' } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('text-lg');
		});
	});

	describe('Disabled state', () => {
		it('is not disabled by default', () => {
			const { container } = render(Button);
			const button = container.querySelector('button') as HTMLButtonElement;
			expect(button.disabled).toBe(false);
		});

		it('can be disabled', () => {
			const { container } = render(Button, { props: { disabled: true } });
			const button = container.querySelector('button') as HTMLButtonElement;
			expect(button.disabled).toBe(true);
		});

		it('applies disabled styling', () => {
			const { container } = render(Button, { props: { disabled: true } });
			const button = container.querySelector('button');
			expect(button?.className).toContain('opacity-50');
		});
	});
});
