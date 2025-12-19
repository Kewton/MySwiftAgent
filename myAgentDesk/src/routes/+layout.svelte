<!--
  Root Layout
  Issue #285: SvelteKit Routing Foundation

  Root layout providing global navigation, breadcrumb, and toast notifications.
-->
<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import GlobalNav from '$lib/components/layout/GlobalNav.svelte';
	import Breadcrumb from '$lib/components/layout/Breadcrumb.svelte';
	import Toast from '$lib/components/ui/Toast.svelte';

	let { children } = $props();

	// Toast state (will be managed by a store in future iterations)
	let toastVisible = $state(false);
	let toastMessage = $state('');
	let toastType: 'info' | 'success' | 'warning' | 'error' = $state('info');
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>MyAgentDesk</title>
</svelte:head>

<div class="app-layout">
	<GlobalNav />
	<Breadcrumb />
	<main class="main-content">
		{@render children()}
	</main>
	<Toast message={toastMessage} type={toastType} visible={toastVisible} />
</div>

<style>
	.app-layout {
		height: 100vh;
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.main-content {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		min-height: 0;
	}
</style>
