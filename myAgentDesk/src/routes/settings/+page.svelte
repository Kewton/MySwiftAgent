<script lang="ts">
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';
	import { locale, type Locale } from '$lib/stores/locale';
	import { get } from 'svelte/store';

	let settings = {
		// General Settings
		userName: 'Agent User',
		language: get(locale) as string,
		timezone: 'UTC',

		// API Settings
		cloudflareApiUrl: '',
		cloudflareApiKey: '',

		// Appearance
		theme: 'auto',
		compactMode: false,

		// Notifications
		emailNotifications: true,
		desktopNotifications: false
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

		// TODO: Implement actual save in Phase 4
		setTimeout(() => {
			saveStatus = 'saved';
			setTimeout(() => {
				saveStatus = 'idle';
			}, 2000);
		}, 1000);
	}

	function handleReset() {
		if (confirm('Are you sure you want to reset all settings to default?')) {
			settings = {
				userName: 'Agent User',
				language: 'en',
				timezone: 'UTC',
				cloudflareApiUrl: '',
				cloudflareApiKey: '',
				theme: 'auto',
				compactMode: false,
				emailNotifications: true,
				desktopNotifications: false
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
				Configure your myAgentDesk preferences and API connections.
			</p>
		</div>

		<div class="space-y-6">
			<!-- General Settings -->
			<Card variant="default">
				<div class="p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">General Settings</h2>
					<div class="space-y-4">
						<div>
							<label
								for="userName"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								User Name
							</label>
							<input
								id="userName"
								type="text"
								bind:value={settings.userName}
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
							/>
						</div>
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
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
									<option value="zh">中文</option>
								</select>
							</div>
							<div>
								<label
									for="timezone"
									class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
								>
									Timezone
								</label>
								<select
									id="timezone"
									bind:value={settings.timezone}
									class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
								>
									<option value="UTC">UTC</option>
									<option value="Asia/Tokyo">Asia/Tokyo</option>
									<option value="America/New_York">America/New_York</option>
									<option value="Europe/London">Europe/London</option>
								</select>
							</div>
						</div>
					</div>
				</div>
			</Card>

			<!-- API Settings (Cloudflare Integration) -->
			<Card variant="default">
				<div class="p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">API Settings</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
						Configure Cloudflare Workers integration for secure backend connections.
					</p>
					<div class="space-y-4">
						<div>
							<label
								for="cloudflareApiUrl"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								Cloudflare API URL
							</label>
							<input
								id="cloudflareApiUrl"
								type="url"
								bind:value={settings.cloudflareApiUrl}
								placeholder="https://your-worker.your-subdomain.workers.dev"
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
							/>
						</div>
						<div>
							<label
								for="cloudflareApiKey"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								API Key
							</label>
							<input
								id="cloudflareApiKey"
								type="password"
								bind:value={settings.cloudflareApiKey}
								placeholder="Enter your API key"
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
							/>
						</div>
						<div class="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
							<span class="text-blue-600 dark:text-blue-400">ℹ️</span>
							<p class="text-sm text-blue-800 dark:text-blue-300">
								Cloudflare integration will be fully implemented in Phase 4. This is currently for
								configuration only.
							</p>
						</div>
					</div>
				</div>
			</Card>

			<!-- Appearance Settings -->
			<Card variant="default">
				<div class="p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Appearance</h2>
					<div class="space-y-4">
						<div>
							<label
								for="theme"
								class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
							>
								Theme
							</label>
							<select
								id="theme"
								bind:value={settings.theme}
								class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-dark-card text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
							>
								<option value="auto">Auto (System)</option>
								<option value="light">Light</option>
								<option value="dark">Dark</option>
							</select>
						</div>
						<div class="flex items-center gap-3">
							<input
								id="compactMode"
								type="checkbox"
								bind:checked={settings.compactMode}
								class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
							/>
							<label for="compactMode" class="text-sm font-medium text-gray-700 dark:text-gray-300">
								Compact Mode
							</label>
						</div>
					</div>
				</div>
			</Card>

			<!-- Notification Settings -->
			<Card variant="default">
				<div class="p-6">
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Notifications</h2>
					<div class="space-y-4">
						<div class="flex items-center gap-3">
							<input
								id="emailNotifications"
								type="checkbox"
								bind:checked={settings.emailNotifications}
								class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
							/>
							<label
								for="emailNotifications"
								class="text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								Email Notifications
							</label>
						</div>
						<div class="flex items-center gap-3">
							<input
								id="desktopNotifications"
								type="checkbox"
								bind:checked={settings.desktopNotifications}
								class="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
							/>
							<label
								for="desktopNotifications"
								class="text-sm font-medium text-gray-700 dark:text-gray-300"
							>
								Desktop Notifications
							</label>
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
