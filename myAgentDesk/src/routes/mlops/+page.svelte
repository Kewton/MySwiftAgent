<script lang="ts">
	/**
	 * MLOps Dashboard Page - Main dashboard with real-time metrics
	 *
	 * Features:
	 * - Real-time metrics via SSE
	 * - Quality metrics cards
	 * - Model usage chart
	 * - Connection status indicator
	 */

	import { onMount, onDestroy } from 'svelte';
	import MetricsCard from '$lib/mlops/components/MetricsCard.svelte';
	import RealtimeChart from '$lib/mlops/components/RealtimeChart.svelte';
	import {
		realtimeStore,
		formattedMetrics,
		currentModelUsage,
		connectionStatus
	} from '$lib/mlops/stores/realtimeStore';
	import { getMetrics } from '$lib/mlops/api/client';
	import type { QualityMetrics, ModelUsage } from '$lib/mlops/types';

	let loading = true;
	let error: string | null = null;
	let staticMetrics: QualityMetrics | null = null;
	let staticModelUsage: ModelUsage[] = [];

	// Use SSE data if connected, otherwise use static data
	$: metrics =
		$connectionStatus.isConnected && $formattedMetrics
			? $formattedMetrics
			: staticMetrics
				? {
						averageScore: `${(staticMetrics.average_score * 100).toFixed(1)}%`,
						totalTurns: staticMetrics.total_turns.toLocaleString(),
						successRate: `${(staticMetrics.success_rate * 100).toFixed(1)}%`,
						averageLatency: `${staticMetrics.average_latency.toFixed(2)}s`,
						totalSessions: staticMetrics.total_sessions.toLocaleString(),
						completionRate: `${(staticMetrics.completion_rate * 100).toFixed(1)}%`
					}
				: null;

	$: modelUsage = $connectionStatus.isConnected ? $currentModelUsage : staticModelUsage;

	onMount(async () => {
		// Start SSE connection
		realtimeStore.connect();

		// Load initial static data as fallback
		try {
			const response = await getMetrics();
			staticMetrics = response.metrics;
			staticModelUsage = response.model_usage;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load metrics';
		} finally {
			loading = false;
		}
	});

	onDestroy(() => {
		realtimeStore.disconnect();
	});
</script>

<svelte:head>
	<title>MLOps Dashboard | myAgentDesk</title>
</svelte:head>

<div class="dashboard" data-testid="mlops-dashboard">
	<!-- Header -->
	<div class="flex items-center justify-between mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">MLOps Dashboard</h1>

		<!-- Connection Status -->
		<div
			class="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm
				{$connectionStatus.isConnected
				? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
				: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}"
			data-testid="connection-status"
		>
			<span
				class="w-2 h-2 rounded-full {$connectionStatus.isConnected
					? 'bg-green-500'
					: 'bg-gray-400'}"
				aria-hidden="true"
			></span>
			<span>{$connectionStatus.isConnected ? 'Live' : 'Offline'}</span>
		</div>
	</div>

	<!-- Error Message -->
	{#if error && !$connectionStatus.isConnected}
		<div
			class="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
			role="alert"
			data-testid="error-message"
		>
			<p class="font-medium">Error loading metrics</p>
			<p class="text-sm mt-1">{error}</p>
		</div>
	{/if}

	<!-- Metrics Grid -->
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
		<MetricsCard
			label="Average Score"
			value={metrics?.averageScore || '-'}
			sublabel="Quality score average"
			variant="success"
			loading={loading && !metrics}
		/>

		<MetricsCard
			label="Total Turns"
			value={metrics?.totalTurns || '-'}
			sublabel="Conversation turns"
			loading={loading && !metrics}
		/>

		<MetricsCard
			label="Success Rate"
			value={metrics?.successRate || '-'}
			sublabel="Successful completions"
			variant="success"
			loading={loading && !metrics}
		/>

		<MetricsCard
			label="Avg Latency"
			value={metrics?.averageLatency || '-'}
			sublabel="Response time"
			loading={loading && !metrics}
		/>

		<MetricsCard
			label="Total Sessions"
			value={metrics?.totalSessions || '-'}
			sublabel="Unique sessions"
			loading={loading && !metrics}
		/>

		<MetricsCard
			label="Completion Rate"
			value={metrics?.completionRate || '-'}
			sublabel="Requirements completed"
			variant="success"
			loading={loading && !metrics}
		/>
	</div>

	<!-- Model Usage Chart -->
	<div class="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
		<RealtimeChart
			data={modelUsage}
			title="Model Usage Distribution"
			loading={loading && modelUsage.length === 0}
		/>
	</div>

	<!-- Last Update -->
	{#if $connectionStatus.lastUpdate}
		<div class="mt-4 text-xs text-gray-500 dark:text-gray-400 text-right">
			Last updated: {new Date($connectionStatus.lastUpdate).toLocaleTimeString()}
		</div>
	{/if}
</div>
