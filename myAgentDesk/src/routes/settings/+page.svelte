<script lang="ts">
	import { locale, t, type Locale } from '$lib/stores/locale';
	import Button from '$lib/components/Button.svelte';
	import Card from '$lib/components/Card.svelte';
	import { goto } from '$app/navigation';

	function setLocale(newLocale: Locale) {
		locale.set(newLocale);
	}

	function goBack() {
		goto('/chat');
	}
</script>

<svelte:head>
	<title>{t('settings.title')} - myAgentDesk</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-dark-bg">
	<!-- Header -->
	<div class="bg-white dark:bg-dark-card border-b border-gray-200 dark:border-gray-800 px-6 py-4">
		<div class="max-w-4xl mx-auto flex items-center justify-between">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">{t('settings.title')}</h1>
			<Button variant="secondary" on:click={goBack}>
				← {t('settings.backToChat')}
			</Button>
		</div>
	</div>

	<!-- Content -->
	<div class="max-w-4xl mx-auto px-6 py-8">
		<Card>
			<div class="space-y-6">
				<!-- Language Settings -->
				<div>
					<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">
						{t('settings.language')}
					</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
						{t('settings.languageDescription')}
					</p>

					<div class="grid grid-cols-2 gap-4">
						<button
							on:click={() => setLocale('ja')}
							class="p-4 rounded-lg border-2 transition-all {$locale === 'ja'
								? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
								: 'border-gray-300 dark:border-gray-700 hover:border-gray-400'}"
						>
							<div class="flex items-center gap-3">
								<div class="text-2xl">🇯🇵</div>
								<div class="text-left">
									<div class="font-medium text-gray-900 dark:text-white">
										{t('settings.japanese')}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">Japanese</div>
								</div>
								{#if $locale === 'ja'}
									<div class="ml-auto">
										<span class="text-primary-600 dark:text-primary-400">✓</span>
									</div>
								{/if}
							</div>
						</button>

						<button
							on:click={() => setLocale('en')}
							class="p-4 rounded-lg border-2 transition-all {$locale === 'en'
								? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
								: 'border-gray-300 dark:border-gray-700 hover:border-gray-400'}"
						>
							<div class="flex items-center gap-3">
								<div class="text-2xl">🇬🇧</div>
								<div class="text-left">
									<div class="font-medium text-gray-900 dark:text-white">
										{t('settings.english')}
									</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">English</div>
								</div>
								{#if $locale === 'en'}
									<div class="ml-auto">
										<span class="text-primary-600 dark:text-primary-400">✓</span>
									</div>
								{/if}
							</div>
						</button>
					</div>
				</div>
			</div>
		</Card>
	</div>
</div>
