<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';

	let darkMode = false;

	onMount(() => {
		// Initialize dark mode from localStorage or system preference
		const stored = localStorage.getItem('darkMode');
		if (stored !== null) {
			darkMode = stored === 'true';
		} else {
			darkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
		}
		updateDarkMode();
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
</script>

<div class="min-h-screen flex flex-col">
	<!-- OpenWebUI inspired Header -->
	<header
		class="sticky top-0 z-50 bg-white dark:bg-dark-bg border-b border-gray-200 dark:border-gray-700"
	>
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex justify-between items-center h-16">
				<div class="flex items-center space-x-4">
					<a href="/" class="text-2xl font-bold text-primary-600 dark:text-primary-400">
						myAgentDesk
					</a>
					<nav class="hidden md:flex space-x-4">
						<a
							href="/"
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
		</div>
	</header>

	<!-- Main content -->
	<main class="flex-1">
		<slot />
	</main>

	<!-- Footer -->
	<footer class="bg-gray-50 dark:bg-dark-card border-t border-gray-200 dark:border-gray-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<p class="text-center text-sm text-gray-600 dark:text-gray-400">
				© 2025 myAgentDesk - AI Agent Desktop Interface
			</p>
		</div>
	</footer>
</div>
