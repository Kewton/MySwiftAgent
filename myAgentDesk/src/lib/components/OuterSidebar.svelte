<script lang="ts">
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { onDestroy } from 'svelte';

	export let expanded = true;
	export let darkMode = false;
	export let onToggleDarkMode: () => void = () => {};
	export let onToggleHistory: () => void = () => {};
	export let onToggleSidebar: () => void = () => {};

	interface MenuItem {
		id: string;
		icon: string;
		label: string;
		path?: string;
		action?: () => void;
		special?: 'darkMode' | 'history';
	}

	const menuItems: MenuItem[] = [
		{ id: 'create', icon: '✏️', label: 'Create Job', path: '/create_job' },
		{ id: 'settings', icon: '⚙️', label: 'Settings', path: '/settings' }
	];

	$: darkModeItem = {
		id: 'dark',
		icon: darkMode ? '🌙' : '☀️',
		label: 'Dark Mode',
		special: 'darkMode' as const
	};

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

	// Normalize paths so active state works for trailing slashes and nested routes
	function normalizePath(path: string): string {
		if (!path) return '';
		if (path.length > 1 && path.endsWith('/')) {
			path = path.slice(0, -1);
		}
		return path || '/';
	}

	const initialPage = get(page);
	let currentPath = normalizePath(initialPage.url.pathname);
	let currentRouteId = initialPage.route.id ?? '';

	const unsubscribe = page.subscribe(($page) => {
		currentPath = normalizePath($page.url.pathname);
		currentRouteId = $page.route.id ?? '';
	});

	onDestroy(unsubscribe);

	function routeMatches(itemPath: string, routeId: string): boolean {
		if (!routeId) return false;
		if (routeId === itemPath) return true;
		if (routeId.startsWith(`${itemPath}/`)) return true;
		if (routeId.endsWith(itemPath)) return true;
		if (itemPath === '/create_job' && routeId === '/') return true;
		return false;
	}

	function pathMatches(itemPath: string, path: string): boolean {
		if (itemPath === '/') {
			return path === '/';
		}

		if (itemPath === '/create_job' && path === '/') {
			return true;
		}

		return path === itemPath || path.startsWith(`${itemPath}/`);
	}

	// Resolve which menu item should be marked active for the current URL
	$: activeMenuId = (() => {
		for (const item of menuItems) {
			if (!item.path) continue;
			const itemPath = normalizePath(item.path);

			if (routeMatches(itemPath, currentRouteId) || pathMatches(itemPath, currentPath)) {
				return item.id;
			}
		}
		return null;
	})();
</script>

<aside
	class="h-screen bg-gray-50 dark:bg-dark-card border-r border-gray-200 dark:border-gray-700 flex flex-col transition-all duration-300"
	class:w-60={expanded}
	class:w-16={!expanded}
	style="overflow-x: clip;"
>
	<!-- Toggle Button -->
	<button
		on:click={onToggleSidebar}
		class="flex items-center gap-3 p-4 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-200 dark:border-gray-700 overflow-hidden"
		aria-label="Toggle sidebar"
	>
		<span class="text-xl">☰</span>
		{#if expanded}
			<span
				class="text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap overflow-hidden text-ellipsis"
				>Menu</span
			>
		{/if}
	</button>

	<!-- Main Navigation -->
	<nav class="flex-1 overflow-y-auto py-4" style="overflow-x: clip;">
		{#each menuItems as item (item.id)}
			<button
				type="button"
				on:click={() => handleMenuClick(item)}
				class="relative w-full flex items-center gap-3 px-4 py-3 transition-colors group overflow-hidden hover:bg-gray-100 dark:hover:bg-gray-700"
				class:bg-primary-100={item.id === activeMenuId}
				class:dark:bg-primary-900={item.id === activeMenuId}
				aria-current={item.id === activeMenuId ? 'page' : undefined}
			>
				<span
					class="absolute inset-y-0 left-0 w-1 rounded-r-full bg-primary-500 dark:bg-primary-400 transition-opacity duration-200"
					class:opacity-100={item.id === activeMenuId}
					class:opacity-0={item.id !== activeMenuId}
				></span>
				<span
					class="text-xl flex-shrink-0 transition-colors"
					class:text-primary-600={item.id === activeMenuId}
					class:dark:text-primary-200={item.id === activeMenuId}
				>
					{item.icon}
				</span>
				{#if expanded}
					<span
						class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap overflow-hidden text-ellipsis transition-colors"
						class:text-primary-700={item.id === activeMenuId}
						class:dark:text-primary-100={item.id === activeMenuId}
						class:font-semibold={item.id === activeMenuId}
					>
						{item.label}
					</span>
				{/if}
				<!-- Tooltip positioned fixed to avoid sidebar overflow -->
				<div
					class="fixed px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[9999]"
					style="left: {expanded ? 'calc(15rem + 0.5rem)' : 'calc(4rem + 0.5rem)'};"
				>
					{item.label}
				</div>
			</button>
		{/each}
	</nav>

	<!-- Bottom Section: Dark Mode Toggle -->
	<div class="border-t border-gray-200 dark:border-gray-700">
		<button
			on:click={() => handleMenuClick(darkModeItem)}
			class="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors group overflow-hidden"
			style="position: relative;"
		>
			<span class="text-xl flex-shrink-0">
				{darkModeItem.icon}
			</span>
			{#if expanded}
				<span
					class="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap overflow-hidden text-ellipsis"
				>
					{darkModeItem.label}
				</span>
			{/if}
			<!-- Tooltip positioned fixed to avoid sidebar overflow -->
			<div
				class="fixed px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-[9999]"
				style="left: {expanded ? 'calc(15rem + 0.5rem)' : 'calc(4rem + 0.5rem)'};"
			>
				{darkModeItem.label}
			</div>
		</button>
	</div>
</aside>
