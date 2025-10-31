<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';

	let darkMode = false;
	const HEADER_HEIGHT = 64;

	onMount(() => {
		// Initialize dark mode from localStorage or system preference
		const stored = localStorage.getItem('darkMode');
		if (stored !== null) {
			darkMode = stored === 'true';
		} else {
			darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		updateDarkMode();
		setLayoutVariables();
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

	function setLayoutVariables() {
		document.documentElement.style.setProperty('--header-height', `${HEADER_HEIGHT}px`);
		if (!document.documentElement.style.getPropertyValue('--sidebar-width')) {
			document.documentElement.style.setProperty('--sidebar-width', '0px');
		}
	}
</script>

<div class="h-screen overflow-hidden bg-white dark:bg-dark-bg">
	<!-- OpenWebUI inspired Header -->
	<header
		class="fixed top-0 right-0 z-50 bg-white dark:bg-dark-bg border-b border-gray-200 dark:border-gray-700 transition-all duration-300"
		style={`left: var(--sidebar-width, 0px); height: var(--header-height, ${HEADER_HEIGHT}px);`}
	>
		<div class="flex items-center justify-between h-full px-4 sm:px-6">
			<div class="flex items-center space-x-4">
				<a href="/create_job" class="text-2xl font-bold text-primary-600 dark:text-primary-400">
					myAgentDesk
				</a>
				<nav class="hidden md:flex space-x-4">
					<a
						href="/create_job"
						class="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 px-3 py-2 rounded-md text-sm font-medium"
					>
						Home
					</a>
					<a
						href="/create_job"
						class="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 px-3 py-2 rounded-md text-sm font-medium"
					>
						Create Job
					</a>
					<a
						href="/settings"
						class="text-gray-700 dark:text-gray-300 hover:text-primary-600 dark:hover:text-primary-400 px-3 py-2 rounded-md text-sm font-medium"
					>
						Settings
					</a>
				</nav>
			</div>
			<div class="flex items-center space-x-4">
				<button
					on:click={toggleDarkMode}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					aria-label="Toggle dark mode"
				>
					{#if darkMode}
						🌙
					{:else}
						☀️
					{/if}
				</button>
			</div>
		</div>
	</header>

	<!-- Main content -->
	<main
		class="h-full transition-all duration-300 overflow-x-hidden overflow-y-auto"
		style={`margin-left: var(--sidebar-width, 0px); margin-top: var(--header-height, ${HEADER_HEIGHT}px); height: calc(100vh - var(--header-height, ${HEADER_HEIGHT}px));`}
	>
		<slot />
	</main>
</div>

<style>
	:global(:root) {
		--header-height: 4rem;
		--sidebar-width: 0px;
	}
</style>
