<!--
  Workbench Dashboard (/projects/:projectId/workbenches/:workbenchId)
  Issue #289: Workbench List/Detail Screens

  Workbench overview page showing statistics and version information.
-->
<script lang="ts">
	import WorkbenchOverview from '$lib/components/workbenches/WorkbenchOverview.svelte';
	import type { WorkbenchDetail } from '$lib/types/workbench';

	interface Props {
		data: {
			workbenchDetail: WorkbenchDetail | null;
		};
	}

	let { data }: Props = $props();
</script>

<div class="overview-page">
	{#if data.workbenchDetail}
		<WorkbenchOverview workbench={data.workbenchDetail} />
	{:else}
		<div class="loading">
			<p>Loading workbench details...</p>
		</div>
	{/if}
</div>

<style>
	.overview-page {
		max-width: 800px;
	}

	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		color: #64748b;
	}
</style>
