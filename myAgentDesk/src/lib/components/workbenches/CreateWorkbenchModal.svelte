<!--
  CreateWorkbenchModal Component
  Issue #289: Workbench List/Detail Screens

  Modal for creating a new workbench (UI only).
  Backend integration will be added in a later issue.
-->
<script lang="ts">
	import type { CreateWorkbenchInput } from '$lib/types/workbench';

	interface Props {
		open: boolean;
		onClose: () => void;
		onCreate?: (input: CreateWorkbenchInput) => void;
	}

	let { open, onClose, onCreate }: Props = $props();

	let name = $state('');
	let description = $state('');
	let isSubmitting = $state(false);

	const isValid = $derived(name.trim().length > 0);

	function handleSubmit(event: Event) {
		event.preventDefault();
		if (!isValid || isSubmitting) return;

		isSubmitting = true;

		const input: CreateWorkbenchInput = {
			name: name.trim(),
			description: description.trim() || undefined
		};

		// Call onCreate callback if provided
		onCreate?.(input);

		// Reset form and close modal
		resetForm();
		onClose();
		isSubmitting = false;
	}

	function resetForm() {
		name = '';
		description = '';
	}

	function handleCancel() {
		resetForm();
		onClose();
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleCancel();
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleCancel();
		}
	}
</script>

{#if open}
	<div
		class="modal-backdrop"
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
		tabindex="-1"
		onclick={handleBackdropClick}
		onkeydown={handleKeydown}
		data-testid="create-workbench-modal"
	>
		<div class="modal-content">
			<div class="modal-header">
				<h2 id="modal-title" class="modal-title">Create New Workbench</h2>
				<button class="close-button" onclick={handleCancel} aria-label="Close modal">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						width="20"
						height="20"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<line x1="18" y1="6" x2="6" y2="18"></line>
						<line x1="6" y1="6" x2="18" y2="18"></line>
					</svg>
				</button>
			</div>

			<form onsubmit={handleSubmit} class="modal-form">
				<div class="form-group">
					<label for="workbench-name" class="form-label">Name <span class="required">*</span></label
					>
					<input
						id="workbench-name"
						type="text"
						class="form-input"
						placeholder="Enter workbench name"
						bind:value={name}
						required
						data-testid="input-name"
					/>
				</div>

				<div class="form-group">
					<label for="workbench-description" class="form-label">Description</label>
					<textarea
						id="workbench-description"
						class="form-textarea"
						placeholder="Enter a description (optional)"
						rows="3"
						bind:value={description}
						data-testid="input-description"
					></textarea>
				</div>

				<div class="modal-footer">
					<button type="button" class="btn btn-secondary" onclick={handleCancel}>Cancel</button>
					<button
						type="submit"
						class="btn btn-primary"
						disabled={!isValid || isSubmitting}
						data-testid="submit-button"
					>
						{#if isSubmitting}
							Creating...
						{:else}
							Create Workbench
						{/if}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgb(0 0 0 / 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
		z-index: 50;
	}

	.modal-content {
		width: 100%;
		max-width: 28rem;
		background: white;
		border-radius: 0.75rem;
		box-shadow: 0 25px 50px -12px rgb(0 0 0 / 0.25);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 1.25rem 1.5rem;
		border-bottom: 1px solid #e2e8f0;
	}

	.modal-title {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.close-button {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 2rem;
		height: 2rem;
		padding: 0;
		background: transparent;
		border: none;
		border-radius: 0.375rem;
		color: #64748b;
		cursor: pointer;
	}

	.close-button:hover {
		background: #f1f5f9;
		color: #1e293b;
	}

	.modal-form {
		padding: 1.5rem;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		margin-bottom: 0.375rem;
	}

	.required {
		color: #dc2626;
	}

	.form-input,
	.form-textarea {
		width: 100%;
		padding: 0.5rem 0.75rem;
		font-size: 0.875rem;
		color: #1e293b;
		background: white;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		transition:
			border-color 0.15s,
			box-shadow 0.15s;
	}

	.form-input:focus,
	.form-textarea:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgb(59 130 246 / 0.1);
	}

	.form-textarea {
		resize: vertical;
		min-height: 5rem;
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		padding-top: 1rem;
		border-top: 1px solid #e2e8f0;
		margin-top: 1rem;
	}

	.btn {
		padding: 0.5rem 1rem;
		font-size: 0.875rem;
		font-weight: 500;
		border-radius: 0.375rem;
		cursor: pointer;
		transition:
			background 0.15s,
			opacity 0.15s;
	}

	.btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.btn-secondary {
		color: #374151;
		background: white;
		border: 1px solid #d1d5db;
	}

	.btn-secondary:hover:not(:disabled) {
		background: #f9fafb;
	}

	.btn-primary {
		color: white;
		background: #3b82f6;
		border: 1px solid transparent;
	}

	.btn-primary:hover:not(:disabled) {
		background: #2563eb;
	}
</style>
