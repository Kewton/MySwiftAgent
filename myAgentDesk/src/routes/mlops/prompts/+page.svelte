<script lang="ts">
	/**
	 * MLOps Prompts Page - Prompt template management
	 *
	 * Features:
	 * - Prompt template list
	 * - Version history
	 * - Prompt editor
	 * - Version activation
	 */

	import { onMount } from 'svelte';
	import PromptVersionList from '$lib/mlops/components/PromptVersionList.svelte';
	import PromptEditor from '$lib/mlops/components/PromptEditor.svelte';
	import PromptViewer from '$lib/mlops/components/PromptViewer.svelte';
	import {
		listPrompts,
		getPrompt,
		createPromptVersion,
		activatePromptVersion
	} from '$lib/mlops/api/client';
	import type { PromptTemplate, PromptVersion } from '$lib/mlops/types';

	let prompts: PromptTemplate[] = [];
	let selectedPrompt: PromptTemplate | null = null;
	let selectedVersion: PromptVersion | null = null;
	let loading = true;
	let saving = false;
	let error: string | null = null;
	let successMessage: string | null = null;
	let editMode = false;

	// Demo data
	const demoPrompts: PromptTemplate[] = [
		{
			id: 'prompt-001',
			name: 'Requirement Clarification',
			description: 'System prompt for requirement clarification dialogue',
			category: 'system',
			current_version: 2,
			versions: [
				{
					id: 'v-001-2',
					version: 2,
					content: `You are a helpful assistant that helps users clarify their job requirements.

Your goal is to extract the following information:
- Data source: Where will the data come from?
- Process: What processing needs to be done?
- Output: What format should the output be in?
- Schedule: When should this job run?

Ask clarifying questions to understand the user's needs.

{{context}}`,
					description: 'Added context variable for conversation history',
					created_at: new Date().toISOString(),
					created_by: 'admin',
					is_active: true,
					metadata: {}
				},
				{
					id: 'v-001-1',
					version: 1,
					content: `You are a helpful assistant that helps users clarify their job requirements.

Ask questions to understand what the user wants to accomplish.`,
					description: 'Initial version',
					created_at: new Date(Date.now() - 86400000).toISOString(),
					created_by: 'admin',
					is_active: false,
					metadata: {}
				}
			],
			created_at: new Date(Date.now() - 86400000 * 7).toISOString(),
			updated_at: new Date().toISOString()
		},
		{
			id: 'prompt-002',
			name: 'Job Generation',
			description: 'Prompt for generating job specifications',
			category: 'generation',
			current_version: 1,
			versions: [
				{
					id: 'v-002-1',
					version: 1,
					content: `Generate a job specification based on the following requirements:

Requirements:
{requirements}

Output a structured job definition in JSON format.`,
					description: 'Initial version',
					created_at: new Date().toISOString(),
					created_by: 'admin',
					is_active: true,
					metadata: {}
				}
			],
			created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
			updated_at: new Date().toISOString()
		}
	];

	async function loadPrompts() {
		loading = true;
		error = null;

		try {
			prompts = await listPrompts();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load prompts';
			prompts = demoPrompts;
		} finally {
			loading = false;
		}
	}

	async function selectPrompt(promptId: string) {
		error = null;
		editMode = false;

		try {
			selectedPrompt = await getPrompt(promptId);
			if (selectedPrompt.versions.length > 0) {
				const activeVersion = selectedPrompt.versions.find((v) => v.is_active);
				selectedVersion = activeVersion || selectedPrompt.versions[0];
			}
		} catch (err) {
			// Use demo data
			selectedPrompt = prompts.find((p) => p.id === promptId) || null;
			if (selectedPrompt && selectedPrompt.versions.length > 0) {
				const activeVersion = selectedPrompt.versions.find((v) => v.is_active);
				selectedVersion = activeVersion || selectedPrompt.versions[0];
			}
		}
	}

	function handleVersionSelect(event: CustomEvent<{ versionId: string }>) {
		if (selectedPrompt) {
			selectedVersion =
				selectedPrompt.versions.find((v) => v.id === event.detail.versionId) || null;
			editMode = false;
		}
	}

	async function handleVersionActivate(event: CustomEvent<{ versionId: string }>) {
		if (!selectedPrompt) return;

		saving = true;
		error = null;

		try {
			await activatePromptVersion(selectedPrompt.id, event.detail.versionId);
			successMessage = 'Version activated successfully';

			// Update local state
			selectedPrompt.versions = selectedPrompt.versions.map((v) => ({
				...v,
				is_active: v.id === event.detail.versionId
			}));
			selectedVersion =
				selectedPrompt.versions.find((v) => v.id === event.detail.versionId) || null;

			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to activate version';
			// Demo behavior: update locally
			if (selectedPrompt) {
				selectedPrompt.versions = selectedPrompt.versions.map((v) => ({
					...v,
					is_active: v.id === event.detail.versionId
				}));
				successMessage = 'Version activated (demo mode)';
				setTimeout(() => {
					successMessage = null;
				}, 3000);
			}
		} finally {
			saving = false;
		}
	}

	async function handleSaveVersion(event: CustomEvent<{ content: string; description: string }>) {
		if (!selectedPrompt) return;

		saving = true;
		error = null;

		try {
			await createPromptVersion({
				prompt_id: selectedPrompt.id,
				content: event.detail.content,
				description: event.detail.description
			});
			successMessage = 'New version created successfully';
			editMode = false;
			await selectPrompt(selectedPrompt.id);

			setTimeout(() => {
				successMessage = null;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to create version';
			// Demo behavior: add locally
			if (selectedPrompt && selectedVersion) {
				const newVersion: PromptVersion = {
					id: `v-${Date.now()}`,
					version: selectedPrompt.current_version + 1,
					content: event.detail.content,
					description: event.detail.description,
					created_at: new Date().toISOString(),
					created_by: 'current-user',
					is_active: false,
					metadata: {}
				};
				selectedPrompt.versions = [newVersion, ...selectedPrompt.versions];
				selectedPrompt.current_version = newVersion.version;
				selectedVersion = newVersion;
				editMode = false;
				successMessage = 'New version created (demo mode)';
				setTimeout(() => {
					successMessage = null;
				}, 3000);
			}
		} finally {
			saving = false;
		}
	}

	function handleCancelEdit() {
		editMode = false;
	}

	function startEdit() {
		editMode = true;
	}

	onMount(() => {
		loadPrompts();
	});
</script>

<svelte:head>
	<title>Prompts | MLOps | myAgentDesk</title>
</svelte:head>

<div class="prompts-page" data-testid="mlops-prompts-page">
	<!-- Header -->
	<div class="mb-6">
		<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100">Prompt Management</h1>
		<p class="text-gray-600 dark:text-gray-400 mt-1">
			Manage and version control your prompt templates
		</p>
	</div>

	<!-- Success Message -->
	{#if successMessage}
		<div
			class="mb-6 p-4 rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
			role="status"
		>
			{successMessage}
		</div>
	{/if}

	<!-- Error Message -->
	{#if error}
		<div
			class="mb-6 p-4 rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400"
			role="alert"
		>
			<p class="font-medium">Note</p>
			<p class="text-sm mt-1">{error} - Using demo mode</p>
		</div>
	{/if}

	<div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
		<!-- Prompt List -->
		<div class="lg:col-span-3 bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
			<h2 class="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">Templates</h2>

			{#if loading}
				<div class="space-y-2 animate-pulse">
					{#each [0, 1, 2] as i (i)}
						<div class="p-3 rounded-lg bg-gray-100 dark:bg-gray-700">
							<div class="h-4 bg-gray-300 dark:bg-gray-600 rounded w-2/3 mb-2"></div>
							<div class="h-3 bg-gray-300 dark:bg-gray-600 rounded w-full"></div>
						</div>
					{/each}
				</div>
			{:else}
				<div class="space-y-2">
					{#each prompts as prompt (prompt.id)}
						<button
							type="button"
							class="w-full text-left p-3 rounded-lg transition-colors
								{selectedPrompt?.id === prompt.id
								? 'bg-blue-100 dark:bg-blue-900/30 border-2 border-blue-500'
								: 'bg-gray-50 dark:bg-gray-700 hover:bg-gray-100 dark:hover:bg-gray-600 border-2 border-transparent'}"
							on:click={() => selectPrompt(prompt.id)}
							data-testid="prompt-item-{prompt.id}"
						>
							<div class="font-medium text-gray-900 dark:text-gray-100 text-sm">
								{prompt.name}
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
								{prompt.description}
							</div>
							<div class="text-xs text-gray-400 dark:text-gray-500 mt-1">
								v{prompt.current_version} - {prompt.category}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Version List -->
		<div class="lg:col-span-3 bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm">
			{#if selectedPrompt}
				<PromptVersionList
					versions={selectedPrompt.versions}
					selectedVersionId={selectedVersion?.id || null}
					loading={saving}
					on:select={handleVersionSelect}
					on:activate={handleVersionActivate}
				/>
			{:else}
				<div class="text-center py-8 text-gray-500 dark:text-gray-400">
					Select a template to view versions
				</div>
			{/if}
		</div>

		<!-- Content View/Editor -->
		<div class="lg:col-span-6 bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm">
			{#if selectedVersion}
				{#if editMode}
					<PromptEditor
						content={selectedVersion.content}
						description=""
						loading={saving}
						on:save={handleSaveVersion}
						on:cancel={handleCancelEdit}
					/>
				{:else}
					<div class="flex items-center justify-between mb-4">
						<div>
							<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">
								Version {selectedVersion.version}
								{#if selectedVersion.is_active}
									<span
										class="ml-2 px-2 py-0.5 text-xs font-medium rounded-full bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
									>
										Active
									</span>
								{/if}
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								{selectedVersion.description}
							</p>
						</div>
						<button
							type="button"
							class="px-4 py-2 rounded-lg font-medium
								bg-blue-600 text-white hover:bg-blue-700
								focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
							on:click={startEdit}
							data-testid="edit-button"
						>
							Create New Version
						</button>
					</div>

					<PromptViewer
						content={selectedVersion.content}
						title="Prompt Content"
						maxHeight="400px"
					/>

					<div class="mt-4 text-xs text-gray-500 dark:text-gray-400">
						Created by {selectedVersion.created_by} on {new Date(
							selectedVersion.created_at
						).toLocaleString()}
					</div>
				{/if}
			{:else}
				<div class="text-center py-12 text-gray-500 dark:text-gray-400">
					<svg
						class="w-16 h-16 mx-auto mb-4 text-gray-300 dark:text-gray-600"
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
					<p class="text-lg font-medium">Select a prompt template</p>
					<p class="mt-2">Choose a template and version to view or edit.</p>
				</div>
			{/if}
		</div>
	</div>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
