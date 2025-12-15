<!--
  Toast Component
  Issue #285: SvelteKit Routing Foundation

  Toast notification component for displaying messages.
  Types: info, success, warning, error
-->
<script lang="ts">
	interface Props {
		message: string;
		type: 'info' | 'success' | 'warning' | 'error';
		visible: boolean;
	}

	let { message, type, visible }: Props = $props();
</script>

{#if visible}
	<div class="toast" data-type={type} role="alert" aria-live="polite">
		<span class="toast-message">{message}</span>
	</div>
{/if}

<style>
	.toast {
		position: fixed;
		bottom: 1.5rem;
		right: 1.5rem;
		padding: 0.75rem 1rem;
		border-radius: 0.5rem;
		box-shadow:
			0 4px 6px -1px rgb(0 0 0 / 0.1),
			0 2px 4px -2px rgb(0 0 0 / 0.1);
		font-size: 0.875rem;
		font-weight: 500;
		z-index: 9999;
		animation: slide-in 0.3s ease-out;
	}

	@keyframes slide-in {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.toast[data-type='info'] {
		background: #eff6ff;
		color: #1e40af;
		border: 1px solid #93c5fd;
	}

	.toast[data-type='success'] {
		background: #f0fdf4;
		color: #166534;
		border: 1px solid #86efac;
	}

	.toast[data-type='warning'] {
		background: #fefce8;
		color: #854d0e;
		border: 1px solid #fde047;
	}

	.toast[data-type='error'] {
		background: #fef2f2;
		color: #991b1b;
		border: 1px solid #fca5a5;
	}

	.toast-message {
		display: block;
	}
</style>
