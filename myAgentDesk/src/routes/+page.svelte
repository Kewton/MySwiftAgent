<script lang="ts">
	import Sidebar from '$lib/components/Sidebar.svelte';
	import ChatBubble from '$lib/components/ChatBubble.svelte';
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';

	let sidebarOpen = true;
	let message = '';

	const demoMessages = [
		{ role: 'user' as const, message: 'Hello! How can I use myAgentDesk?', timestamp: '10:30 AM' },
		{
			role: 'assistant' as const,
			message:
				'Welcome to myAgentDesk! You can manage AI agents, create workflows, and integrate with Cloudflare for secure backend connections. Try exploring the Agents page to see available agents.',
			timestamp: '10:31 AM'
		},
		{
			role: 'user' as const,
			message: 'What kind of workflows can I create?',
			timestamp: '10:32 AM'
		},
		{
			role: 'assistant' as const,
			message:
				'You can create visual workflows connecting multiple agents, similar to Dify. Drag and drop nodes, configure connections, and orchestrate complex AI pipelines. Check out the workflow builder in the next phase!',
			timestamp: '10:33 AM'
		}
	];

	function toggleSidebar() {
		sidebarOpen = !sidebarOpen;
	}

	function handleSend() {
		if (message.trim()) {
			// TODO: Implement message sending in Phase 4
			console.log('Sending message:', message);
			message = '';
		}
	}
</script>

<svelte:head>
	<title>myAgentDesk - Home</title>
</svelte:head>

<!-- OpenWebUI-style Layout -->
<div class="flex h-[calc(100vh-4rem)]">
	<!-- Sidebar -->
	<Sidebar isOpen={sidebarOpen} />

	<!-- Main Content -->
	<div class="flex-1 flex flex-col">
		<!-- Header with sidebar toggle -->
		<div class="border-b border-gray-200 dark:border-gray-700 px-4 py-3 flex items-center gap-4">
			<button
				on:click={toggleSidebar}
				class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
				aria-label="Toggle sidebar"
			>
				{#if sidebarOpen}
					◀
				{:else}
					☰
				{/if}
			</button>
			<h1 class="text-xl font-semibold text-gray-900 dark:text-white">AI Chat</h1>
		</div>

		<!-- Chat Area (OpenWebUI style) -->
		<div class="flex-1 overflow-y-auto px-4 py-6 space-y-4">
			{#each demoMessages as msg}
				<ChatBubble role={msg.role} message={msg.message} timestamp={msg.timestamp} />
			{/each}
		</div>

		<!-- Input Area -->
		<div class="border-t border-gray-200 dark:border-gray-700 p-4">
			<div class="max-w-4xl mx-auto">
				<div class="flex gap-2">
					<input
						type="text"
						bind:value={message}
						placeholder="Type your message here..."
						class="flex-1 px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
						on:keypress={(e) => e.key === 'Enter' && handleSend()}
					/>
					<Button variant="primary" size="lg" on:click={handleSend}>Send</Button>
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 text-center">
					OpenWebUI-inspired interface • Powered by myAgentDesk
				</p>
			</div>
		</div>
	</div>
</div>

<!-- Quick Start Guide (shown when no sidebar) -->
{#if !sidebarOpen}
	<div class="fixed bottom-4 left-4 max-w-xs">
		<Card variant="default" hoverable>
			<div class="p-4">
				<h3 class="text-sm font-semibold mb-2">💡 Quick Tip</h3>
				<p class="text-xs text-gray-600 dark:text-gray-400">
					Click the ☰ menu to open the sidebar and access your conversation history.
				</p>
			</div>
		</Card>
	</div>
{/if}
