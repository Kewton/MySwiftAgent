/**
 * Conversation Store - チャット履歴管理
 *
 * 機能:
 * - 会話の作成・読み込み・更新・削除
 * - localStorageへの自動保存
 * - アクティブな会話の管理
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { createEmptyRequirements, type JobResult, type RequirementState } from '$lib/domain/types';

export interface Message {
	role: 'user' | 'assistant';
	message: string;
	timestamp: string;
}

export interface Conversation {
	id: string;
	title: string;
	createdAt: number;
	updatedAt: number;
	messages: Message[];
	requirements: RequirementState;
	jobResult?: JobResult;
}

interface ConversationStoreState {
	conversations: Conversation[];
	activeId: string | null;
}

const STORAGE_KEY = 'myAgentDesk_conversations';
const MAX_CONVERSATIONS = 100; // 保存する最大会話数

/**
 * localStorageから会話履歴を読み込み
 */
function loadFromStorage(): ConversationStoreState {
	if (!browser) {
		return { conversations: [], activeId: null };
	}

	try {
		const stored = localStorage.getItem(STORAGE_KEY);
		if (stored) {
			const parsed = JSON.parse(stored);
			// 古い会話を削除（最大保存数を超える場合）
			if (parsed.conversations.length > MAX_CONVERSATIONS) {
				parsed.conversations = parsed.conversations
					.sort((a: Conversation, b: Conversation) => b.updatedAt - a.updatedAt)
					.slice(0, MAX_CONVERSATIONS);
			}
			return parsed;
		}
	} catch (error) {
		console.error('Failed to load conversations from localStorage:', error);
	}

	return { conversations: [], activeId: null };
}

/**
 * localStorageへ会話履歴を保存
 */
function saveToStorage(state: ConversationStoreState) {
	if (!browser) return;

	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
	} catch (error) {
		console.error('Failed to save conversations to localStorage:', error);
	}
}

/**
 * タイトルを生成（最初のユーザーメッセージから）
 */
function generateTitle(firstMessage: string): string {
	const trimmed = firstMessage.trim();
	return trimmed.length > 40 ? trimmed.substring(0, 40) + '...' : trimmed;
}

/**
 * Conversation Store
 */
function createConversationStore() {
	const initialState = loadFromStorage();
	const { subscribe, set, update } = writable<ConversationStoreState>(initialState);

	// localStorageへ自動保存
	subscribe((value) => {
		saveToStorage(value);
	});

	return {
		subscribe,

		/**
		 * 新しい会話を作成
		 */
		create: (): Conversation => {
			const newConv: Conversation = {
				id: `conv_${Date.now()}_${Math.random().toString(36).substring(7)}`,
				title: '新しいジョブ',
				createdAt: Date.now(),
				updatedAt: Date.now(),
				messages: [],
				requirements: createEmptyRequirements()
			};

			update((state) => ({
				conversations: [newConv, ...state.conversations],
				activeId: newConv.id
			}));

			return newConv;
		},

		/**
		 * アクティブな会話を設定
		 */
		setActive: (id: string) => {
			update((state) => {
				const exists = state.conversations.some((c) => c.id === id);
				if (!exists) {
					console.warn(`Conversation ${id} not found`);
					return state;
				}
				return { ...state, activeId: id };
			});
		},

		/**
		 * 会話を更新
		 */
		update: (id: string, updates: Partial<Conversation>) => {
			update((state) => ({
				...state,
				conversations: state.conversations.map((conv) =>
					conv.id === id ? { ...conv, ...updates, updatedAt: Date.now() } : conv
				)
			}));
		},

		/**
		 * メッセージを追加
		 */
		addMessage: (id: string, message: Message) => {
			update((state) => {
				const conversations = state.conversations.map((conv) => {
					if (conv.id === id) {
						const newMessages = [...conv.messages, message];
						// 最初のユーザーメッセージの場合、タイトルを自動生成
						const title =
							conv.title === '新しいジョブ' && message.role === 'user'
								? generateTitle(message.message)
								: conv.title;
						return {
							...conv,
							messages: newMessages,
							title,
							updatedAt: Date.now()
						};
					}
					return conv;
				});

				return { ...state, conversations };
			});
		},

		/**
		 * 最後のアシスタントメッセージを更新（ストリーミング用）
		 */
		updateLastAssistantMessage: (id: string, message: string) => {
			update((state) => {
				const conversations = state.conversations.map((conv) => {
					if (conv.id === id) {
						const messages = [...conv.messages];
						const lastIdx = messages.length - 1;
						if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
							messages[lastIdx] = { ...messages[lastIdx], message };
						}
						return { ...conv, messages, updatedAt: Date.now() };
					}
					return conv;
				});

				return { ...state, conversations };
			});
		},

		/**
		 * 要求状態を更新
		 */
		updateRequirements: (id: string, requirements: RequirementState) => {
			update((state) => ({
				...state,
				conversations: state.conversations.map((conv) =>
					conv.id === id ? { ...conv, requirements, updatedAt: Date.now() } : conv
				)
			}));
		},

		/**
		 * ジョブ結果を保存
		 */
		saveJobResult: (id: string, jobResult: JobResult) => {
			update((state) => ({
				...state,
				conversations: state.conversations.map((conv) =>
					conv.id === id ? { ...conv, jobResult, updatedAt: Date.now() } : conv
				)
			}));
		},

		/**
		 * 会話を削除
		 */
		delete: (id: string) => {
			update((state) => {
				const conversations = state.conversations.filter((c) => c.id !== id);
				const activeId = state.activeId === id ? null : state.activeId;
				return { conversations, activeId };
			});
		},

		/**
		 * タイトルを変更
		 */
		updateTitle: (id: string, title: string) => {
			update((state) => ({
				...state,
				conversations: state.conversations.map((conv) =>
					conv.id === id ? { ...conv, title, updatedAt: Date.now() } : conv
				)
			}));
		},

		/**
		 * すべての会話をクリア
		 */
		clear: () => {
			set({ conversations: [], activeId: null });
		}
	};
}

export const conversationStore = createConversationStore();

/**
 * アクティブな会話を取得（派生Store）
 */
export const activeConversation = derived(
	conversationStore,
	($store) => $store.conversations.find((c) => c.id === $store.activeId) || null
);

/**
 * 会話をソート（最新順）
 */
export const sortedConversations = derived(conversationStore, ($store) =>
	[...$store.conversations].sort((a, b) => b.updatedAt - a.updatedAt)
);

/**
 * 日付グルーピング用の会話リスト
 */
export const groupedConversations = derived(sortedConversations, ($conversations) => {
	const now = Date.now();
	const oneDayMs = 24 * 60 * 60 * 1000;
	const sevenDaysMs = 7 * oneDayMs;

	const groups = {
		today: [] as Conversation[],
		yesterday: [] as Conversation[],
		lastSevenDays: [] as Conversation[],
		older: [] as Conversation[]
	};

	$conversations.forEach((conv) => {
		const age = now - conv.updatedAt;
		if (age < oneDayMs) {
			groups.today.push(conv);
		} else if (age < 2 * oneDayMs) {
			groups.yesterday.push(conv);
		} else if (age < sevenDaysMs) {
			groups.lastSevenDays.push(conv);
		} else {
			groups.older.push(conv);
		}
	});

	return groups;
});
