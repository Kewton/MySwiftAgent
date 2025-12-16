<!--
  WorkbenchStatusFilter Component
  Issue #289: Workbench List/Detail Screens

  URL-driven status filter for workbench list.
  Updates URL query params when filter changes.
-->
<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import type { WorkbenchStatusCounts, WorkbenchStatusFilter } from '$lib/types/workbench';

	interface Props {
		counts: WorkbenchStatusCounts;
	}

	let { counts }: Props = $props();

	const currentFilter = $derived(
		($page.url.searchParams.get('status') as WorkbenchStatusFilter) || 'all'
	);

	const filters: { value: WorkbenchStatusFilter; label: string }[] = [
		{ value: 'all', label: 'All' },
		{ value: 'active', label: 'Active' },
		{ value: 'draft', label: 'Draft' },
		{ value: 'archived', label: 'Archived' }
	];

	function setFilter(status: WorkbenchStatusFilter) {
		const url = new URL($page.url);
		if (status === 'all') {
			url.searchParams.delete('status');
		} else {
			url.searchParams.set('status', status);
		}
		goto(url.toString(), { replaceState: true, noScroll: true });
	}

	function getCount(status: WorkbenchStatusFilter): number {
		return counts[status];
	}
</script>

<div class="filter-container" data-testid="status-filter">
	{#each filters as filter (filter.value)}
		<button
			class="filter-button"
			class:active={currentFilter === filter.value}
			onclick={() => setFilter(filter.value)}
			data-testid="filter-{filter.value}"
		>
			{filter.label}
			<span class="count">{getCount(filter.value)}</span>
		</button>
	{/each}
</div>

<style>
	.filter-container {
		display: flex;
		gap: 0.5rem;
		padding: 0.25rem;
		background: #f8fafc;
		border-radius: 0.5rem;
	}

	.filter-button {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		font-weight: 500;
		color: #64748b;
		background: transparent;
		border: none;
		border-radius: 0.375rem;
		cursor: pointer;
		transition:
			background 0.15s,
			color 0.15s;
	}

	.filter-button:hover {
		background: #e2e8f0;
		color: #1e293b;
	}

	.filter-button.active {
		background: white;
		color: #1e293b;
		box-shadow: 0 1px 2px rgb(0 0 0 / 0.05);
	}

	.count {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 1.25rem;
		height: 1.25rem;
		padding: 0 0.375rem;
		font-size: 0.75rem;
		font-weight: 600;
		background: #e2e8f0;
		border-radius: 9999px;
	}

	.filter-button.active .count {
		background: #3b82f6;
		color: white;
	}
</style>
