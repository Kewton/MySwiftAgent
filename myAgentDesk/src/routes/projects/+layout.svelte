<!--
  Projects Layout
  Issue #285: SvelteKit Routing Foundation

  Layout for projects area - minimal wrapper.
-->
<script lang="ts">
	let { children } = $props();
</script>

<div class="projects-layout">
	{@render children()}
</div>

<style>
	.projects-layout {
		flex: 1;
		display: flex;
		flex-direction: column;
		width: 100%;
		min-height: 0;
		overflow: hidden;
	}
</style>
