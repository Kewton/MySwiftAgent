<script lang="ts">
	/**
	 * FeedbackModal - Modal wrapper for feedback form
	 *
	 * Features:
	 * - Modal overlay with backdrop
	 * - Escape key to close
	 * - Click outside to close
	 * - Focus trap
	 * - Accessible dialog
	 */

	import { createEventDispatcher, onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import FeedbackForm from './FeedbackForm.svelte';
	import type { FeedbackScores } from '../types';

	export let open = false;
	export let conversationId: string;
	export let loading = false;

	const dispatch = createEventDispatcher<{
		submit: FeedbackScores;
		close: void;
	}>();

	let modalElement: HTMLDivElement;
	let previousActiveElement: HTMLElement | null = null;

	function handleKeyDown(event: KeyboardEvent) {
		if (event.key === 'Escape' && open && !loading) {
			event.preventDefault();
			handleClose();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget && !loading) {
			handleClose();
		}
	}

	function handleClose() {
		if (!loading) {
			dispatch('close');
		}
	}

	function handleSubmit(event: CustomEvent<FeedbackScores>) {
		dispatch('submit', event.detail);
	}

	function handleCancel() {
		handleClose();
	}

	function handleBackdropKeyDown(event: KeyboardEvent) {
		// Prevent closing on Tab key - let it cycle through focusable elements
		if (event.key === 'Tab') {
			if (!modalElement) return;

			const focusableElements = modalElement.querySelectorAll(
				'button:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
			);

			if (focusableElements.length === 0) return;

			const firstElement = focusableElements[0] as HTMLElement;
			const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement;

			if (event.shiftKey && document.activeElement === firstElement) {
				event.preventDefault();
				lastElement.focus();
			} else if (!event.shiftKey && document.activeElement === lastElement) {
				event.preventDefault();
				firstElement.focus();
			}
		}
	}

	onMount(() => {
		if (open && browser) {
			previousActiveElement = document.activeElement as HTMLElement;
			document.body.style.overflow = 'hidden';
		}
	});

	onDestroy(() => {
		if (browser) {
			document.body.style.overflow = '';
			if (previousActiveElement) {
				previousActiveElement.focus();
			}
		}
	});

	$: if (browser && open) {
		previousActiveElement = document.activeElement as HTMLElement;
		document.body.style.overflow = 'hidden';
		// Focus modal on next tick
		setTimeout(() => {
			if (modalElement) {
				const firstFocusable = modalElement.querySelector(
					'button:not([disabled]), textarea:not([disabled])'
				) as HTMLElement;
				firstFocusable?.focus();
			}
		}, 0);
	} else if (browser) {
		document.body.style.overflow = '';
		if (previousActiveElement) {
			previousActiveElement.focus();
		}
	}
</script>

<svelte:window on:keydown={handleKeyDown} />

{#if open}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
		role="presentation"
		data-testid="feedback-modal"
	>
		<!-- Backdrop click handler -->
		<button
			type="button"
			class="absolute inset-0 w-full h-full cursor-default bg-transparent border-0"
			on:click={handleBackdropClick}
			on:keydown={handleBackdropKeyDown}
			aria-label="Close modal"
			tabindex="-1"
		></button>
		<div
			bind:this={modalElement}
			role="dialog"
			aria-modal="true"
			aria-labelledby="feedback-modal-title"
			class="relative w-full max-w-lg bg-white dark:bg-gray-900 rounded-xl shadow-2xl overflow-hidden"
		>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center justify-between">
					<h2
						id="feedback-modal-title"
						class="text-xl font-semibold text-gray-900 dark:text-gray-100"
					>
						Rate Your Experience
					</h2>
					<button
						type="button"
						class="p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300
							hover:bg-gray-100 dark:hover:bg-gray-800
							focus:ring-2 focus:ring-gray-500 focus:ring-offset-2
							disabled:opacity-50 disabled:cursor-not-allowed"
						disabled={loading}
						on:click={handleClose}
						aria-label="Close modal"
						data-testid="close-modal-button"
					>
						<svg
							class="w-5 h-5"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
							aria-hidden="true"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>
				<p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
					Your feedback helps us improve the requirement clarification experience.
				</p>
			</div>

			<!-- Form -->
			<div class="px-6 py-4 max-h-[60vh] overflow-y-auto">
				<FeedbackForm
					{conversationId}
					{loading}
					on:submit={handleSubmit}
					on:cancel={handleCancel}
				/>
			</div>
		</div>
	</div>
{/if}
