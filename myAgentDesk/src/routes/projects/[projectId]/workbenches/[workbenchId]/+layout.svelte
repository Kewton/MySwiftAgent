<!--
  Workbench Layout
  Issue #285: SvelteKit Routing Foundation

  Layout for workbench pages with tab navigation and next action bar.
-->
<script lang="ts">
	import WorkbenchTabs from '$lib/components/layout/WorkbenchTabs.svelte';
	import NextActionBar from '$lib/components/layout/NextActionBar.svelte';
	import { page } from '$app/stores';
	import type { Snippet } from 'svelte';

	interface Props {
		data: {
			workbench: {
				id: string;
				name: string;
				projectId: string;
			};
		};
		children: Snippet;
	}

	let { data, children }: Props = $props();

	// Determine next action based on current page
	const currentPath = $derived($page.url.pathname);
	const basePath = $derived(
		`/projects/${data.workbench.projectId}/workbenches/${data.workbench.id}`
	);

	const nextAction = $derived.by(() => {
		if (currentPath.includes('/requirements')) {
			return {
				message: 'Requirements ready? Generate your job.',
				actionLabel: 'Generate Job',
				actionHref: `${basePath}/generate`,
				visible: true
			};
		}
		if (currentPath.includes('/generate')) {
			return {
				message: 'Generation complete? Review the results.',
				actionLabel: 'Review Results',
				actionHref: `${basePath}/review`,
				visible: true
			};
		}
		if (currentPath.includes('/review')) {
			return {
				message: 'Looks good? Start a run.',
				actionLabel: 'Start Run',
				actionHref: `${basePath}/runs`,
				visible: true
			};
		}
		if (currentPath.includes('/runs') && !currentPath.includes('/runs/')) {
			return {
				message: 'Run complete? Analyze the results.',
				actionLabel: 'Analyze Results',
				actionHref: `${basePath}/analyze`,
				visible: true
			};
		}
		if (currentPath.includes('/analyze')) {
			return {
				message: 'Found improvements? Update requirements.',
				actionLabel: 'Improve Requirements',
				actionHref: `${basePath}/improve`,
				visible: true
			};
		}
		return { message: '', actionLabel: '', actionHref: '', visible: false };
	});
</script>

<div class="workbench-layout">
	<div class="workbench-header">
		<h2 class="workbench-name">{data.workbench.name}</h2>
	</div>
	<WorkbenchTabs workbench={data.workbench} />
	<div class="workbench-content">
		{@render children()}
	</div>
	<NextActionBar
		message={nextAction.message}
		actionLabel={nextAction.actionLabel}
		actionHref={nextAction.actionHref}
		visible={nextAction.visible}
	/>
</div>

<style>
	.workbench-layout {
		display: flex;
		flex-direction: column;
		flex: 1;
		min-height: 0;
		background: white;
		border-radius: 0.5rem;
		border: 1px solid #e2e8f0;
		overflow: hidden;
	}

	.workbench-header {
		padding: 1rem 1.5rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.workbench-name {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.workbench-content {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
	}
</style>
