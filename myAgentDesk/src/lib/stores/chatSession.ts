import { get, writable } from 'svelte/store';
import { activeConversation, conversationStore, type Message } from './conversations';
import { streamChatRequirementDefinition, createJob, ServiceError } from '$lib/services';
import type { RequirementState } from '$lib/domain/types';
import { t } from './locale';

interface ChatSessionState {
	isStreaming: boolean;
	isCreatingJob: boolean;
	lastError: string | null;
	scrollToken: number;
}

const INITIAL_STATE: ChatSessionState = {
	isStreaming: false,
	isCreatingJob: false,
	lastError: null,
	scrollToken: 0
};

export const COMPLETENESS_THRESHOLD = 0.8;

function formatTimestamp(): string {
	const now = new Date();
	return now.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
}

function resolveErrorMessage(error: unknown): string {
	if (error instanceof ServiceError) return error.message;
	if (error instanceof Error) return error.message;
	return t('error.general');
}

function safeAlert(message: string) {
	if (typeof window !== 'undefined') {
		alert(message);
	}
}

export const chatSession = (() => {
	let state = { ...INITIAL_STATE };
	const { subscribe, update } = writable<ChatSessionState>({ ...INITIAL_STATE });

	subscribe((value) => {
		state = value;
	});

	function requestScroll() {
		update((state) => ({ ...state, scrollToken: state.scrollToken + 1 }));
	}

	function setStreaming(value: boolean) {
		update((state) => ({ ...state, isStreaming: value }));
	}

	function setCreating(value: boolean) {
		update((state) => ({ ...state, isCreatingJob: value }));
	}

	function setError(message: string | null) {
		update((state) => ({ ...state, lastError: message }));
	}

	async function sendMessage(rawMessage: string) {
		const trimmed = rawMessage.trim();
		if (!trimmed) return;

		const conversation = get(activeConversation);
		if (!conversation) {
			setError(t('alert.noConversation'));
			return;
		}

		if (state.isStreaming) return;

		const { id: conversationId, requirements } = conversation;
		const previousMessages = conversation.messages.map((msg) => ({
			role: msg.role,
			content: msg.message
		}));

		const timestamp = formatTimestamp();
		const userMessage: Message = {
			role: 'user',
			message: trimmed,
			timestamp
		};

		conversationStore.addMessage(conversationId, userMessage);
		requestScroll();
		setStreaming(true);
		setError(null);

		let assistantMessage = '';
		let hasAddedAssistantMessage = false;

		try {
			await streamChatRequirementDefinition(
				conversationId,
				trimmed,
				previousMessages,
				requirements,
				(content: string) => {
					assistantMessage += content;
					if (!hasAddedAssistantMessage) {
						const assistant: Message = {
							role: 'assistant',
							message: assistantMessage,
							timestamp: formatTimestamp()
						};
						conversationStore.addMessage(conversationId, assistant);
						hasAddedAssistantMessage = true;
					} else {
						conversationStore.updateLastAssistantMessage(conversationId, assistantMessage);
					}
					requestScroll();
				},
				(updatedRequirements: RequirementState) => {
					conversationStore.updateRequirements(conversationId, updatedRequirements);
				}
			);
		} catch (error) {
			console.error('Error streaming chat:', error);
			const message = resolveErrorMessage(error);
			const assistant: Message = {
				role: 'assistant',
				message,
				timestamp: formatTimestamp()
			};
			conversationStore.addMessage(conversationId, assistant);
			setError(message);
			requestScroll();
		} finally {
			setStreaming(false);
		}
	}

	async function submitJob() {
		const conversation = get(activeConversation);
		if (!conversation) {
			setError(t('alert.noConversation'));
			return;
		}

		const { id: conversationId, requirements } = conversation;

		if (!isRequirementsReady(requirements)) {
			const message = t(
				'alert.insufficientRequirements',
				(requirements.completeness * 100).toFixed(0)
			);
			setError(message);
			safeAlert(message);
			return;
		}

		setCreating(true);
		setError(null);

		try {
			const result = await createJob(conversationId, requirements);
			conversationStore.saveJobResult(conversationId, result);

			const success: Message = {
				role: 'assistant',
				message: t('job.createSuccess', result.job_id, result.job_master_id),
				timestamp: formatTimestamp()
			};

			conversationStore.addMessage(conversationId, success);
			requestScroll();
		} catch (error) {
			console.error('Error creating job:', error);
			const message = `❌ **${t('error.jobCreation')}** ${resolveErrorMessage(error)}`;
			conversationStore.addMessage(conversationId, {
				role: 'assistant',
				message,
				timestamp: formatTimestamp()
			});
			setError(message);
			requestScroll();
		} finally {
			setCreating(false);
		}
	}

	function isRequirementsReady(requirements: RequirementState): boolean {
		return requirements.completeness >= COMPLETENESS_THRESHOLD;
	}

	function clearError() {
		setError(null);
	}

	return {
		subscribe,
		sendMessage,
		submitJob,
		clearError,
		isRequirementsReady,
		COMPLETENESS_THRESHOLD
	};
})();

export type ChatSessionStore = typeof chatSession;
