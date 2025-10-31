/**
 * MessageInput Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import MessageInput from './MessageInput.svelte';

describe('MessageInput', () => {
	it('should render with initial props', () => {
		const { getByPlaceholderText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		expect(getByPlaceholderText(/売上データを分析/i)).toBeTruthy();
	});

	it('should call onSend when send button is clicked', async () => {
		const onSend = vi.fn();

		const { getByRole } = render(MessageInput, {
			props: {
				message: 'テストメッセージ',
				isStreaming: false,
				isComposing: false,
				onSend,
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const button = getByRole('button', { name: /送信/i });
		await fireEvent.click(button);

		expect(onSend).toHaveBeenCalledTimes(1);
	});

	it('should disable textarea when isStreaming is true', () => {
		const { getByPlaceholderText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: true,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const textarea = getByPlaceholderText(/売上データを分析/i) as HTMLTextAreaElement;
		expect(textarea.disabled).toBe(true);
	});

	it('should disable send button when message is empty', () => {
		const { getByRole } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const button = getByRole('button');
		expect(button.hasAttribute('disabled')).toBe(true);
	});

	it('should disable send button when isStreaming is true', () => {
		const { getByRole } = render(MessageInput, {
			props: {
				message: 'テスト',
				isStreaming: true,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const button = getByRole('button');
		expect(button.hasAttribute('disabled')).toBe(true);
	});

	it('should enable send button when message is not empty and not streaming', () => {
		const { getByRole } = render(MessageInput, {
			props: {
				message: 'テストメッセージ',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const button = getByRole('button');
		expect(button.hasAttribute('disabled')).toBe(false);
	});

	it('should call onKeydown when key is pressed', async () => {
		const onKeydown = vi.fn();

		const { getByPlaceholderText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown,
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		const textarea = getByPlaceholderText(/売上データを分析/i);
		await fireEvent.keyDown(textarea, { key: 'Enter' });

		expect(onKeydown).toHaveBeenCalled();
	});

	it('should call onCompositionStart when IME starts', async () => {
		const onCompositionStart = vi.fn();

		const { getByPlaceholderText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart,
				onCompositionEnd: vi.fn()
			}
		});

		const textarea = getByPlaceholderText(/売上データを分析/i);
		await fireEvent.compositionStart(textarea);

		expect(onCompositionStart).toHaveBeenCalled();
	});

	it('should call onCompositionEnd when IME ends', async () => {
		const onCompositionEnd = vi.fn();

		const { getByPlaceholderText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd
			}
		});

		const textarea = getByPlaceholderText(/売上データを分析/i);
		await fireEvent.compositionEnd(textarea);

		expect(onCompositionEnd).toHaveBeenCalled();
	});

	it('should show composing indicator when isComposing is true', () => {
		const { getByText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: false,
				isComposing: true,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		expect(getByText(/変換中/i)).toBeTruthy();
	});

	it('should show loading icon when isStreaming is true', () => {
		const { getByText } = render(MessageInput, {
			props: {
				message: '',
				isStreaming: true,
				isComposing: false,
				onSend: vi.fn(),
				onKeydown: vi.fn(),
				onCompositionStart: vi.fn(),
				onCompositionEnd: vi.fn()
			}
		});

		expect(getByText('⏳')).toBeTruthy();
	});
});
