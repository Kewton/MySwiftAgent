<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import OuterSidebar from '$lib/components/OuterSidebar.svelte';
	import { innerSidebarOpen } from '$lib/stores/sidebar';

	let darkMode = false;
	let outerSidebarExpanded = true;

	const OUTER_SIDEBAR_WIDTH_EXPANDED = 240;
	const OUTER_SIDEBAR_WIDTH_COLLAPSED = 64;

	onMount(() => {
		// Initialize dark mode from localStorage or system preference
		const stored = localStorage.getItem('darkMode');
		if (stored !== null) {
			darkMode = stored === 'true';
		} else {
			darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		updateDarkMode();

		// Initialize outer sidebar state
		const storedSidebar = localStorage.getItem('outerSidebarExpanded');
		if (storedSidebar !== null) {
			outerSidebarExpanded = storedSidebar === 'true';
		}
		updateLayoutVariables();
	});

	function toggleDarkMode() {
		darkMode = !darkMode;
		updateDarkMode();
		localStorage.setItem('darkMode', darkMode.toString());
	}

	function updateDarkMode() {
		if (darkMode) {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	}

	function toggleInnerSidebar() {
		innerSidebarOpen.update((v) => !v);
	}

	function updateLayoutVariables() {
		const width = outerSidebarExpanded
			? OUTER_SIDEBAR_WIDTH_EXPANDED
			: OUTER_SIDEBAR_WIDTH_COLLAPSED;
		document.documentElement.style.setProperty('--outer-sidebar-width', `${width}px`);
	}

	$: {
		outerSidebarExpanded;
		updateLayoutVariables();
		localStorage.setItem('outerSidebarExpanded', outerSidebarExpanded.toString());
	}
</script>

<div class="h-screen overflow-hidden bg-white dark:bg-dark-bg flex">
	<!-- Outer Sidebar (VS Code style) -->
	<OuterSidebar
		bind:expanded={outerSidebarExpanded}
		bind:darkMode
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
