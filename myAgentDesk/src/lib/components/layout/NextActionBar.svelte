<!--
  NextActionBar Component
  Issue #285: SvelteKit Routing Foundation

  Displays contextual "next action" guidance at the bottom of workbench pages.
  Guides users through the improvement loop workflow.
-->
<script lang="ts">
	interface Props {
		message: string;
		actionLabel: string;
		actionHref: string;
		visible?: boolean;
	}

	let { message, actionLabel, actionHref, visible = true }: Props = $props();
</script>

{#if visible}
	<aside class="next-action-bar" role="region" aria-label="Next action">
		<div class="action-content">
			<span class="action-message">{message}</span>
			<a href={actionHref} class="action-button" aria-label={actionLabel}>
				{actionLabel}
			</a>
		</div>
	</aside>
{/if}

<style>
	.next-action-bar {
		position: sticky;
		bottom: 0;
		background: linear-gradient(to right, #eff6ff, #f0fdf4);
		border-top: 1px solid #e2e8f0;
		padding: 0.75rem 1rem;
		z-index: 100;
	}

	.action-content {
		display: flex;
		align-items: center;
		justify-content: space-between;
		max-width: 1200px;
		margin: 0 auto;
	}

	.action-message {
		color: #475569;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.action-button {
		display: inline-flex;
		align-items: center;
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		text-decoration: none;
		font-size: 0.875rem;
		font-weight: 600;
		border-radius: 0.375rem;
		transition:
			background 0.15s,
			transform 0.1s;
	}

	.action-button:hover {
		background: #2563eb;
	}

	.action-button:active {
		transform: scale(0.98);
	}
</style>
