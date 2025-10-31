/**
 * Chat API Service Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { streamChatRequirementDefinition } from './chat-api';
import { ServiceError } from './types';
import type { Message, RequirementState } from './types';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('streamChatRequirementDefinition', () => {
	const conversationId = 'test-conv-123';
	const userMessage = 'テストメッセージ';
	const previousMessages: Message[] = [
		{ role: 'user', content: '前のメッセージ' },
		{ role: 'assistant', content: '返信' }
	];
	const requirements: RequirementState = {
		data_source: null,
		process_description: null,
		output_format: null,
		schedule: null,
		completeness: 0
	};

	beforeEach(() => {
		mockFetch.mockReset();
	});

	it('should successfully stream messages', async () => {
		// Mock SSE stream
		const mockReader = {
			read: vi
				.fn()
				.mockResolvedValueOnce({
					done: false,
					value: new TextEncoder().encode(
						'data: {"type":"message","data":{"content":"こんにちは"}}\n'
					)
				})
				.mockResolvedValueOnce({
					done: false,
					value: new TextEncoder().encode('data: {"type":"message","data":{"content":"！"}}\n')
				})
				.mockResolvedValueOnce({ done: true, value: undefined })
		};

		mockFetch.mockResolvedValue({
			ok: true,
			body: {
				getReader: () => mockReader
			}
		});

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		await streamChatRequirementDefinition(
			conversationId,
			userMessage,
			previousMessages,
			requirements,
			onMessage,
			onRequirementUpdate
		);

		const [url, options] = mockFetch.mock.calls[0];
		expect(url).toBe('http://localhost:8104/aiagent-api/v1/chat/requirement-definition');
		expect(options?.method).toBe('POST');
		expect(options?.headers).toBeInstanceOf(Headers);
		expect((options?.headers as Headers).get('Content-Type')).toBe('application/json');
		expect(options?.body).toBe(
			JSON.stringify({
				conversation_id: conversationId,
				user_message: userMessage,
				context: {
					previous_messages: previousMessages,
					current_requirements: requirements
				}
			})
		);

		expect(onMessage).toHaveBeenCalledTimes(2);
		expect(onMessage).toHaveBeenNthCalledWith(1, 'こんにちは');
		expect(onMessage).toHaveBeenNthCalledWith(2, '！');
	});

	it('should handle requirement updates', async () => {
		const updatedRequirements: RequirementState = {
			data_source: 'CSV file',
			process_description: 'データ分析',
			output_format: 'Excel',
			schedule: '毎日',
			completeness: 0.8
		};

		const mockReader = {
			read: vi
				.fn()
				.mockResolvedValueOnce({
					done: false,
					value: new TextEncoder().encode(
						`data: {"type":"requirement_update","data":{"requirements":${JSON.stringify(updatedRequirements)}}}\n`
					)
				})
				.mockResolvedValueOnce({ done: true, value: undefined })
		};

		mockFetch.mockResolvedValue({
			ok: true,
			body: {
				getReader: () => mockReader
			}
		});

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		await streamChatRequirementDefinition(
			conversationId,
			userMessage,
			previousMessages,
			requirements,
			onMessage,
			onRequirementUpdate
		);

		expect(onRequirementUpdate).toHaveBeenCalledTimes(1);
		expect(onRequirementUpdate).toHaveBeenCalledWith(updatedRequirements);
	});

	it('should throw ServiceError on network failure', async () => {
		mockFetch.mockRejectedValue(new Error('Network error'));

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow(ServiceError);

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow('Failed to connect to chat API');
	});

	it('should throw ServiceError on HTTP error', async () => {
		mockFetch.mockResolvedValue({
			ok: false,
			status: 500,
			statusText: 'Internal Server Error'
		});

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow(ServiceError);

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow('HTTP 500: Internal Server Error');
	});

	it('should throw ServiceError when body is not readable', async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			body: null
		});

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow(ServiceError);

		await expect(
			streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			)
		).rejects.toThrow('Response body is not readable');
	});

	it('should handle invalid JSON in stream', async () => {
		const mockReader = {
			read: vi
				.fn()
				.mockResolvedValueOnce({
					done: false,
					value: new TextEncoder().encode('data: invalid json\n')
				})
				.mockResolvedValueOnce({ done: true, value: undefined })
		};

		mockFetch.mockResolvedValue({
			ok: true,
			body: {
				getReader: () => mockReader
			}
		});

		const onMessage = vi.fn();
		const onRequirementUpdate = vi.fn();

		try {
			await streamChatRequirementDefinition(
				conversationId,
				userMessage,
				previousMessages,
				requirements,
				onMessage,
				onRequirementUpdate
			);
			// Should not reach here
			expect(true).toBe(false);
		} catch (error) {
			expect(error).toBeInstanceOf(ServiceError);
			expect((error as ServiceError).message).toBe('Error processing stream data');
		}
	});
});
