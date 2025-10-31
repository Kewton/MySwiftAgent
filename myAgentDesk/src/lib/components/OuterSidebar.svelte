<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	export let expanded = true;
	export let darkMode = false;
	export let onToggleDarkMode: () => void = () => {};
	export let onToggleHistory: () => void = () => {};

	interface MenuItem {
		id: string;
		icon: string;
		label: string;
		path?: string;
		action?: () => void;
		special?: 'darkMode' | 'history';
	}

	const menuItems: MenuItem[] = [
		{ id: 'home', icon: '🔥', label: 'Home', path: '/' },
		{ id: 'create', icon: '✏️', label: 'Create Job', path: '/create_job' },
		{ id: 'history', icon: '📜', label: 'History', special: 'history' },
		{ id: 'settings', icon: '⚙️', label: 'Settings', path: '/settings' }
	];

	$: darkModeItem = {
		id: 'dark',
		icon: darkMode ? '🌙' : '☀️',
		label: 'Dark Mode',
		special: 'darkMode' as const
	};

	function toggleExpanded() {
		expanded = !expanded;
	}

	function handleMenuClick(item: MenuItem) {
		if (item.special === 'darkMode') {
			onToggleDarkMode();
		} else if (item.special === 'history') {
			onToggleHistory();
		} else if (item.path) {
			goto(item.path);
		} else if (item.action) {
			item.action();
		}
	}

	function isActive(item: MenuItem): boolean {
		if (!item.path) return false;
		// Exact match for most paths, but allow /create_job to match both / and /create_job
		if (item.path === '/' && ($page.url.pathname === '/' || $page.url.pathname === '/create_job')) {
			// Home is active on both / and /create_job if we're not on /create_job specifically
			return $page.url.pathname === '/';
		}
		return $page.url.pathname === item.path;
	}
</script>

<aside
	class="h-screen bg-gray-50 dark:bg-dark-card border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300"
	class:w-60={expanded}
	class:w-16={!expanded}
>
	<!-- Toggle Button -->
	<button
		on:click={toggleExpanded}
		class="flex items-center gap-3 p-4 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-200 dark:border-gray-700"
		aria-label="Toggle sidebar"
	>
		<span class="text-xl">☰</span>
		{#if expanded}
			<span class="text-sm font-medium text-gray-900 dark:text-white">Menu</span>
		{/if}
	</button>

	<!-- Main Navigation -->
	<nav class="flex-1 overflow-y-auto py-4">
		{#each menuItems as item (item.id)}
			<button
				on:click={() => handleMenuClick(item)}
				class="w-full flex items-center gap-3 px-4 py-3 transition-colors group relative {isActive(
					item
				)
					? 'bg-primary-100 dark:bg-primary-900'
					: 'hover:bg-gray-100 dark:hover:bg-gray-700'}"
				title={!expanded ? item.label : ''}
			>
				<span class="text-xl flex-shrink-0">{item.icon}</span>
				{#if expanded}
					<span
						class="text-sm font-medium whitespace-nowrap"
						class:text-primary-600={isActive(item)}
						class:dark:text-primary-400={isActive(item)}
						class:text-gray-700={!isActive(item)}
						class:dark:text-gray-300={!isActive(item)}
					>
						{item.label}
					</span>
				{:else}
					<!-- Tooltip on hover when collapsed -->
					<div
						class="absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
					>
						{item.label}
					</div>
				{/if}
			</button>
		{/each}
	</nav>

	<!-- Bottom Section: Dark Mode Toggle -->
	<div class="border-t border-gray-200 dark:border-gray-700">
		<button
			on:click={() => handleMenuClick(darkModeItem)}
			class="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group relative"
			title={!expanded ? darkModeItem.label : ''}
		>
			<span class="text-xl flex-shrink-0">{darkModeItem.icon}</span>
			{#if expanded}
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap">
					{darkModeItem.label}
				</span>
			{:else}
				<!-- Tooltip on hover when collapsed -->
				<div
					class="absolute left-full ml-2 px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50"
				>
					{darkModeItem.label}
				</div>
			{/if}
		</button>
	</div>
</aside>
