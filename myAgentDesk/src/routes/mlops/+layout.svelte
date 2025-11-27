<script lang="ts">
	/**
	 * MLOps Layout - Shared layout for MLOps pages
	 *
	 * Features:
	 * - Navigation sidebar
	 * - Responsive design
	 * - Dark mode support
	 */

	import { page } from '$app/stores';

	const navItems = [
		{ href: '/mlops', label: 'Dashboard', icon: 'dashboard' },
		{ href: '/mlops/chat', label: 'Chat', icon: 'chat' },
		{ href: '/mlops/diagnostics', label: 'Diagnostics', icon: 'diagnostics' },
		{ href: '/mlops/prompts', label: 'Prompts', icon: 'prompts' }
	];

	function isActive(href: string, pathname: string): boolean {
		if (href === '/mlops') {
			return pathname === '/mlops';
		}
		return pathname.startsWith(href);
	}
</script>

<div class="mlops-layout h-full flex" data-testid="mlops-layout">
	<!-- Sidebar Navigation -->
	<aside
		class="w-64 bg-gray-50 dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex-shrink-0 hidden md:block"
		aria-label="MLOps navigation"
	>
		<div class="p-4">
			<h1 class="text-xl font-bold text-gray-900 dark:text-gray-100 mb-6">MLOps Dashboard</h1>

			<nav class="space-y-1">
				{#each navItems as item}
					<a
						href={item.href}
						class="flex items-center gap-3 px-3 py-2 rounded-lg transition-colors
							{isActive(item.href, $page.url.pathname)
							? 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400'
							: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 hover:text-gray-900 dark:hover:text-gray-100'}"
						aria-current={isActive(item.href, $page.url.pathname) ? 'page' : undefined}
						data-testid="nav-{item.icon}"
					>
						{#if item.icon === 'dashboard'}
							<svg
								class="w-5 h-5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
								/>
							</svg>
						{:else if item.icon === 'chat'}
							<svg
								class="w-5 h-5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
								/>
							</svg>
						{:else if item.icon === 'diagnostics'}
							<svg
								class="w-5 h-5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
								/>
							</svg>
						{:else if item.icon === 'prompts'}
							<svg
								class="w-5 h-5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
								aria-hidden="true"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
								/>
							</svg>
						{/if}
						<span class="font-medium">{item.label}</span>
					</a>
				{/each}
			</nav>
		</div>
	</aside>

	<!-- Mobile Navigation -->
	<div
		class="md:hidden fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 z-50"
	>
		<nav class="flex justify-around py-2">
			{#each navItems as item}
				<a
					href={item.href}
					class="flex flex-col items-center gap-1 px-3 py-1 rounded transition-colors
						{isActive(item.href, $page.url.pathname)
						? 'text-blue-600 dark:text-blue-400'
						: 'text-gray-500 dark:text-gray-400'}"
					aria-current={isActive(item.href, $page.url.pathname) ? 'page' : undefined}
				>
					{#if item.icon === 'dashboard'}
						<svg
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
							/>
						</svg>
					{:else if item.icon === 'chat'}
						<svg
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
							/>
						</svg>
					{:else if item.icon === 'diagnostics'}
						<svg
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
							/>
						</svg>
					{:else if item.icon === 'prompts'}
						<svg
							class="w-6 h-6"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
							/>
						</svg>
					{/if}
					<span class="text-xs">{item.label}</span>
				</a>
			{/each}
		</nav>
	</div>

	<!-- Main Content -->
	<main class="flex-1 overflow-y-auto pb-16 md:pb-0">
		<div class="p-6">
			<slot />
		</div>
	</main>
</div>
