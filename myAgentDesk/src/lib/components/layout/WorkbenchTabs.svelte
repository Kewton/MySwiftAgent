<!--
  WorkbenchTabs Component
  Issue #285: SvelteKit Routing Foundation

  Tab navigation for workbench-level pages.
  Tabs: Requirements, Generate, Review, Runs, Analyze, Improve, Schedule
-->
<script lang="ts">
	import { page } from '$app/stores';

	interface Workbench {
		id: string;
		name: string;
		projectId: string;
	}

	interface Props {
		workbench: Workbench;
	}

	let { workbench }: Props = $props();

	const currentPath = $derived($page.url.pathname);
	const basePath = $derived(`/projects/${workbench.projectId}/workbenches/${workbench.id}`);

	const tabs = [
		{ label: 'Requirements', path: 'requirements' },
		{ label: 'Generate', path: 'generate' },
		{ label: 'Review', path: 'review' },
		{ label: 'Runs', path: 'runs' },
		{ label: 'Analyze', path: 'analyze' },
		{ label: 'Improve', path: 'improve' },
		{ label: 'Schedule', path: 'schedule' }
	];

	function isActive(tabPath: string): boolean {
		const fullPath = `${basePath}/${tabPath}`;
		return currentPath.startsWith(fullPath);
	}
</script>

<nav class="workbench-tabs" aria-label="Workbench navigation">
	<div class="tabs-container">
		{#each tabs as tab (tab.path)}
			<a
				href="{basePath}/{tab.path}"
				class="tab"
				class:active={isActive(tab.path)}
				aria-label={tab.label}
			>
				{tab.label}
			</a>
		{/each}
	</div>
</nav>

<style>
	.workbench-tabs {
		flex-shrink: 0;
		background: white;
		border-bottom: 1px solid #e2e8f0;
		padding: 0 1rem;
	}

	.tabs-container {
		display: flex;
		gap: 0;
		overflow-x: auto;
	}

	.tab {
		display: flex;
		align-items: center;
		padding: 0.75rem 1rem;
		color: #64748b;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 500;
		border-bottom: 2px solid transparent;
		transition:
			color 0.15s,
			border-color 0.15s;
		white-space: nowrap;
	}

	.tab:hover {
		color: #1e293b;
	}

	.tab.active {
		color: #3b82f6;
		border-bottom-color: #3b82f6;
	}
</style>
