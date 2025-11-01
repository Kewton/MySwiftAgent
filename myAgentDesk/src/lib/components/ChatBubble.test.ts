import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import ChatBubble from './ChatBubble.svelte';

describe('ChatBubble.svelte', () => {
	describe('Rendering', () => {
		it('renders with required props', () => {
			const { container } = render(ChatBubble, {
				props: { message: 'Hello world' }
			});
			const bubble = container.querySelector('.chat-bubble');
			expect(bubble).toBeTruthy();
		});

		it('displays the message text', () => {
			const { getByText } = render(ChatBubble, {
				props: { message: 'Test message' }
			});
			expect(getByText('Test message')).toBeTruthy();
		});
	});

	describe('Roles', () => {
		it('applies user role styling by default', () => {
			const { container } = render(ChatBubble, {
				props: { role: 'user', message: 'User message' }
			});
			const bubble = container.querySelector('.chat-bubble');
			expect(bubble?.className).toContain('max-w-3xl');
			expect(bubble?.className).toContain('bg-primary-50');
		});

		it('applies assistant role styling', () => {
			const { container } = render(ChatBubble, {
				props: { role: 'assistant', message: 'Assistant message' }
			});
			const bubble = container.querySelector('.chat-bubble');
			expect(bubble?.className).toContain('w-full');
		});

		it('does not display icon for user role', () => {
			const { container } = render(ChatBubble, {
				props: { role: 'user', message: 'Message' }
			});
			expect(container.textContent).not.toContain('👤');
			expect(container.textContent).not.toContain('🔥');
		});

		it('displays fire icon for assistant role', () => {
			const { container } = render(ChatBubble, {
				props: { role: 'assistant', message: 'Message' }
			});
			expect(container.textContent).toContain('🔥');
		});
	});

	describe('Timestamp', () => {
		it('displays timestamp when provided', () => {
			const { getByText } = render(ChatBubble, {
				props: {
					message: 'Message',
					timestamp: '10:30 AM'
				}
			});
			expect(getByText('10:30 AM')).toBeTruthy();
		});

		it('does not display timestamp when not provided', () => {
			const { container } = render(ChatBubble, {
				props: { message: 'Message' }
			});
			const timestamps = container.querySelectorAll('.text-xs');
			expect(timestamps.length).toBe(0);
		});
	});
});
