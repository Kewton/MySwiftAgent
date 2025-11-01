<script lang="ts">
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';
	import { locale, type Locale } from '$lib/stores/locale';
	import { get } from 'svelte/store';

	let settings = {
		language: get(locale) as string
	};

	let saveStatus: 'idle' | 'saving' | 'saved' | 'error' = 'idle';

	// Watch for language changes and update locale store
	$: {
		if (settings.language === 'ja' || settings.language === 'en') {
			locale.set(settings.language as Locale);
		}
	}

	function handleSave() {
		saveStatus = 'saving';

		// Update locale store
		if (settings.language === 'ja' || settings.language === 'en') {
			locale.set(settings.language as Locale);
		}

		setTimeout(() => {
			saveStatus = 'saved';
			setTimeout(() => {
				saveStatus = 'idle';
			}, 2000);
		}, 1000);
	}

	function handleReset() {
		if (confirm('Are you sure you want to reset language to default?')) {
			settings = {
				language: 'en'
			};
			locale.set('en');
		}
	}
</script>

<svelte:head>
	<title>myAgentDesk - Settings</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-dark-bg">
	<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">Settings</h1>
			<p class="text-gray-600 dark:text-gray-400">
				Configure your myAgentDesk language preferences.
			</p>
		</div>

		<div class="space-y-6">
			<!-- Language Settings -->
			<Card variant="default">
				<div class="p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">
						Language Settings
					</h2>
					<div class="space-y-4">
						<div>
							<label
								for="language"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								Language
							</label>
							<select
								id="language"
								bind:value={settings.language}
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
							>
								<option value="en">English</option>
								<option value="ja">日本語</option>
							</select>
						</div>
					</div>
				</div>
			</Card>

			<!-- Action Buttons -->
			<div class="flex gap-4 justify-end">
				<Button variant="secondary" on:click={handleReset}>Reset to Default</Button>
				<Button variant="primary" on:click={handleSave} disabled={saveStatus === 'saving'}>
					{#if saveStatus === 'saving'}
						Saving...
					{:else if saveStatus === 'saved'}
						✓ Saved
					{:else}
						Save Settings
					{/if}
				</Button>
			</div>
		</div>
	</div>
</div>
