<!--
  Project Layout
  Issue #285: SvelteKit Routing Foundation

  Layout for project detail pages with sidebar navigation.
-->
<script lang="ts">
	import ProjectSidebar from '$lib/components/layout/ProjectSidebar.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		data: {
			project: {
				id: string;
				name: string;
			};
		};
		children: Snippet;
	}

	let { data, children }: Props = $props();
</script>

<div class="project-layout">
	<ProjectSidebar project={data.project} />
	<div class="project-content">
		{@render children()}
	</div>
</div>

<style>
	.project-layout {
		display: flex;
		flex: 1;
		min-height: 0;
		height: 100%;
		overflow: hidden;
	}

	.project-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		overflow: hidden;
		padding: 1.5rem;
		background: #f8fafc;
	}
</style>
