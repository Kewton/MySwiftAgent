/**
 * Real-time Dashboard Store - SSE-based real-time metrics store
 *
 * Features:
 * - SSE connection management
 * - Automatic reconnection
 * - Metrics caching
 * - Connection state tracking
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { subscribeToDashboard } from '../api/client';
import type { QualityMetrics, ModelUsage, DashboardSSEEvent } from '../types';

// ============================================================================
// Store State Types
// ============================================================================

interface RealtimeStoreState {
	metrics: QualityMetrics | null;
	modelUsage: ModelUsage[];
	isConnected: boolean;
	lastUpdate: string | null;
	error: string | null;
	clientId: string | null;
}

// ============================================================================
// Initial State
// ============================================================================

const initialState: RealtimeStoreState = {
	metrics: null,
	modelUsage: [],
	isConnected: false,
	lastUpdate: null,
	error: null,
	clientId: null
};

// ============================================================================
// Store Implementation
// ============================================================================

function createRealtimeStore() {
	const { subscribe, set, update } = writable<RealtimeStoreState>(initialState);

	let unsubscribe: (() => void) | null = null;
	let reconnectAttempts = 0;
	const MAX_RECONNECT_ATTEMPTS = 5;
	const RECONNECT_DELAY = 3000;

	/**
	 * Handle SSE events
	 */
	function handleEvent(event: DashboardSSEEvent) {
		update((state) => {
			switch (event.event_type) {
				case 'connected':
					return {
						...state,
						isConnected: true,
						clientId: event.data.client_id || null,
						error: null
					};

				case 'metrics_update':
					return {
						...state,
						metrics: event.data.metrics || state.metrics,
						modelUsage: event.data.model_usage || state.modelUsage,
						lastUpdate: event.timestamp,
						error: null
					};

				case 'heartbeat':
					return {
						...state,
						lastUpdate: event.timestamp
					};

				case 'error':
					return {
						...state,
						error: event.data.error || 'Unknown error'
					};

				default:
					return state;
			}
		});

		// Reset reconnect attempts on successful event
		reconnectAttempts = 0;
	}

	/**
	 * Handle SSE errors with reconnection logic
	 */
	function handleError(error: Error) {
		update((state) => ({
			...state,
			isConnected: false,
			error: error.message
		}));

		// Attempt reconnection
		if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
			reconnectAttempts++;
			setTimeout(() => {
				connect();
			}, RECONNECT_DELAY * reconnectAttempts);
		}
	}

	/**
	 * Connect to SSE stream
	 */
	function connect() {
		if (!browser) return;

		// Close existing connection
		if (unsubscribe) {
			unsubscribe();
		}

		update((state) => ({
			...state,
			error: null
		}));

		unsubscribe = subscribeToDashboard(handleEvent, handleError);
	}

	/**
	 * Disconnect from SSE stream
	 */
	function disconnect() {
		if (unsubscribe) {
			unsubscribe();
			unsubscribe = null;
		}

		update((state) => ({
			...state,
			isConnected: false,
			clientId: null
		}));
	}

	/**
	 * Reset the store to initial state
	 */
	function reset() {
		disconnect();
		set(initialState);
		reconnectAttempts = 0;
	}

	return {
		subscribe,

		/**
		 * Start real-time connection
		 */
		connect,

		/**
		 * Stop real-time connection
		 */
		disconnect,

		/**
		 * Reset store state
		 */
		reset,

		/**
		 * Get current connection status
		 */
		get isConnected() {
			return get({ subscribe }).isConnected;
		}
	};
}

// ============================================================================
// Export Store Instance
// ============================================================================

export const realtimeStore = createRealtimeStore();

// ============================================================================
// Derived Stores
// ============================================================================

/**
 * Current metrics (convenience accessor)
 */
export const currentMetrics = derived(realtimeStore, ($store) => $store.metrics);

/**
 * Current model usage (convenience accessor)
 */
export const currentModelUsage = derived(realtimeStore, ($store) => $store.modelUsage);

/**
 * Connection status (convenience accessor)
 */
export const connectionStatus = derived(realtimeStore, ($store) => ({
	isConnected: $store.isConnected,
	error: $store.error,
	lastUpdate: $store.lastUpdate
}));

/**
 * Formatted metrics for display
 */
export const formattedMetrics = derived(realtimeStore, ($store) => {
	if (!$store.metrics) return null;

	const m = $store.metrics;
	return {
		averageScore: `${(m.average_score * 100).toFixed(1)}%`,
		totalTurns: m.total_turns.toLocaleString(),
		successRate: m.success_rate !== undefined ? `${(m.success_rate * 100).toFixed(1)}%` : '-',
		averageLatency: m.average_latency !== undefined ? `${m.average_latency.toFixed(2)}s` : '-',
		totalSessions: m.total_sessions.toLocaleString(),
		completionRate: `${(m.completion_rate * 100).toFixed(1)}%`
	};
});
