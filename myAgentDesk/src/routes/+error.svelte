<!--
  Error Page
  Issue #285: SvelteKit Routing Foundation

  Global error page for handling 404, 500, and other errors.
-->
<script lang="ts">
	import { page } from '$app/stores';

	const status = $derived($page.status);
	const message = $derived($page.error?.message || 'An error occurred');
</script>

<div class="error-page">
	<div class="error-content">
		<h1 class="error-status">{status}</h1>
		<p class="error-message">{message}</p>
		<div class="error-actions">
			<a href="/" class="home-link">Go to Home</a>
			<button class="back-button" onclick={() => history.back()}>Go Back</button>
		</div>
	</div>
</div>

<style>
	.error-page {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: 2rem;
	}

	.error-content {
		text-align: center;
		max-width: 400px;
	}

	.error-status {
		font-size: 6rem;
		font-weight: 700;
		color: #e2e8f0;
		margin: 0;
		line-height: 1;
	}

	.error-message {
		font-size: 1.125rem;
		color: #64748b;
		margin: 1rem 0 2rem;
	}

	.error-actions {
		display: flex;
		gap: 1rem;
		justify-content: center;
	}

	.home-link,
	.back-button {
		padding: 0.625rem 1.25rem;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.375rem;
		cursor: pointer;
		transition:
			background 0.15s,
			border-color 0.15s;
	}

	.home-link {
		background: #3b82f6;
		color: white;
		text-decoration: none;
	}

	.home-link:hover {
		background: #2563eb;
	}

	.back-button {
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
	}

	.back-button:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}
</style>
