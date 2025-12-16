<!--
  Workbench Dashboard (/projects/:projectId/workbenches/:workbenchId)
  Issue #285: SvelteKit Routing Foundation

  Workbench overview - typically redirects to requirements tab.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { onMount } from 'svelte';

	const projectId = $derived($page.params.projectId);
	const workbenchId = $derived($page.params.workbenchId);

	// Redirect to requirements tab by default
	onMount(() => {
		goto(`/projects/${projectId}/workbenches/${workbenchId}/requirements`, { replaceState: true });
	});
</script>

<div class="loading">
	<p>Loading workbench...</p>
</div>

<style>
	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 200px;
		color: #64748b;
	}
</style>
