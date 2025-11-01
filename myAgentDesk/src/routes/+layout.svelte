<script lang="ts">
	import '../app.css';
	import { browser } from '$app/environment';
	import OuterSidebar from '$lib/components/OuterSidebar.svelte';
	import { innerSidebarOpen } from '$lib/stores/sidebar';
	import { layoutStore, toggleDarkMode, toggleOuterSidebar } from '$lib/stores/layout';

	export let data;
	export let params;

	const OUTER_SIDEBAR_WIDTH_EXPANDED = 240;
	const OUTER_SIDEBAR_WIDTH_COLLAPSED = 64;

	function toggleInnerSidebar() {
		innerSidebarOpen.update((v) => !v);
	}

	$: if (browser) {
		const width = $layoutStore.outerSidebarExpanded
			? OUTER_SIDEBAR_WIDTH_EXPANDED
			: OUTER_SIDEBAR_WIDTH_COLLAPSED;
		document.documentElement.style.setProperty('--outer-sidebar-width', `${width}px`);
	}
</script>

<div class="h-screen overflow-hidden bg-white dark:bg-dark-bg flex">
	<!-- Outer Sidebar (VS Code style) -->
	<OuterSidebar
		expanded={$layoutStore.outerSidebarExpanded}
		darkMode={$layoutStore.darkMode}
		onToggleSidebar={toggleOuterSidebar}
		onToggleDarkMode={toggleDarkMode}
		onToggleHistory={toggleInnerSidebar}
	/>

	<!-- Main content -->
	<main class="flex-1 overflow-hidden">
		<slot />
	</main>
</div>

<style>
	:global(:root) {
		--outer-sidebar-width: 240px;
		--inner-sidebar-width: 256px;
	}
</style>
