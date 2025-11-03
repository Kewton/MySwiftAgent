<script lang="ts">
	import AgentCard from '$lib/components/AgentCard.svelte';
	import Button from '$lib/components/Button.svelte';

	type AgentColor = 'purple' | 'pink' | 'orange' | 'blue';
	type AgentStatus = 'active' | 'inactive' | 'error';

	interface Agent {
		id: number;
		name: string;
		description: string;
		icon: string;
		color: AgentColor;
		status: AgentStatus;
		category: string;
	}

	const agents: Agent[] = [
		{
			id: 1,
			name: 'Content Generator',
			description:
				'Generate high-quality content using advanced language models. Perfect for blogs, articles, and marketing copy.',
			icon: '✍️',
			color: 'purple',
			status: 'active',
			category: 'Content'
		},
		{
			id: 2,
			name: 'Code Assistant',
			description:
				'AI-powered coding companion that helps with code generation, debugging, and optimization across multiple languages.',
			icon: '💻',
			color: 'blue',
			status: 'active',
			category: 'Development'
		},
		{
			id: 3,
			name: 'Data Analyst',
			description:
				'Analyze datasets, generate insights, and create visualizations. Supports CSV, JSON, and SQL databases.',
			icon: '📊',
			color: 'orange',
			status: 'inactive',
			category: 'Analytics'
		},
		{
			id: 4,
			name: 'Image Creator',
			description:
				'Generate stunning images from text descriptions using state-of-the-art diffusion models.',
			icon: '🎨',
			color: 'pink',
			status: 'active',
			category: 'Creative'
		},
		{
			id: 5,
			name: 'Workflow Orchestrator',
			description:
				'Connect multiple agents in visual workflows. Inspired by Dify for maximum flexibility and control.',
			icon: '🔗',
			color: 'purple',
			status: 'inactive',
			category: 'Automation'
		},
		{
			id: 6,
			name: 'Translation Expert',
			description:
				'Translate text between 100+ languages while preserving context, tone, and cultural nuances.',
			icon: '🌐',
			color: 'blue',
			status: 'error',
			category: 'Language'
		}
	];

	let searchQuery = '';
	let selectedCategory = 'All';

	const categories = [
		'All',
		'Content',
		'Development',
		'Analytics',
		'Creative',
		'Automation',
		'Language'
	];

	$: filteredAgents = agents.filter((agent) => {
		const matchesSearch =
			agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
			agent.description.toLowerCase().includes(searchQuery.toLowerCase());
		const matchesCategory = selectedCategory === 'All' || agent.category === selectedCategory;
		return matchesSearch && matchesCategory;
	});
</script>

<svelte:head>
	<title>myAgentDesk - Agents</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-dark-bg">
	<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">AI Agents</h1>
			<p class="text-gray-600 dark:text-gray-400">
				Discover and manage your AI agents. Dify-inspired node cards for visual workflow building.
			</p>
		</div>

		<!-- Filters (Dify-style) -->
		<div class="mb-6 space-y-4">
			<!-- Search -->
			<div class="flex flex-col sm:flex-row gap-4">
				<input
					type="text"
					bind:value={searchQuery}
					placeholder="Search agents..."
					class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
				/>
				<Button variant="primary">+ New Agent</Button>
			</div>

			<!-- Category Filter -->
			<div class="flex flex-wrap gap-2">
				{#each categories as category}
					<button
						on:click={() => (selectedCategory = category)}
						class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {selectedCategory ===
						category
							? 'bg-primary-500 text-white'
							: 'bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'}"
					>
						{category}
					</button>
				{/each}
			</div>
		</div>

		<!-- Agent Grid (Dify-style node cards) -->
		{#if filteredAgents.length > 0}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				{#each filteredAgents as agent (agent.id)}
					<AgentCard
						name={agent.name}
						description={agent.description}
						icon={agent.icon}
						color={agent.color}
						status={agent.status}
					/>
				{/each}
			</div>
		{:else}
			<div class="text-center py-12">
				<div class="text-6xl mb-4">🔍</div>
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">No agents found</h3>
				<p class="text-gray-600 dark:text-gray-400">
					Try adjusting your search or filter criteria.
				</p>
			</div>
		{/if}

		<!-- Stats -->
		<div class="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
			<div class="bg-white dark:bg-dark-card rounded-lg p-6 shadow-sm">
				<div class="text-3xl font-bold text-primary-600 dark:text-primary-400 mb-2">
					{agents.length}
				</div>
				<div class="text-sm text-gray-600 dark:text-gray-400">Total Agents</div>
			</div>
			<div class="bg-white dark:bg-dark-card rounded-lg p-6 shadow-sm">
				<div class="text-3xl font-bold text-green-600 dark:text-green-400 mb-2">
					{agents.filter((a) => a.status === 'active').length}
				</div>
				<div class="text-sm text-gray-600 dark:text-gray-400">Active Agents</div>
			</div>
			<div class="bg-white dark:bg-dark-card rounded-lg p-6 shadow-sm">
				<div class="text-3xl font-bold text-accent-purple mb-2">
					{categories.length - 1}
				</div>
				<div class="text-sm text-gray-600 dark:text-gray-400">Categories</div>
			</div>
		</div>
	</div>
</div>
