<!--
  EditableText Component

  Inline editable text field with edit/save/cancel functionality.
  Uses SvelteKit form actions for server-side persistence.
-->
<script lang="ts">
	import { enhance } from '$app/forms';

	interface Props {
		value: string | null;
		placeholder?: string;
		action: string;
		fieldName?: string;
		multiline?: boolean;
		emptyText?: string;
	}

	let {
		value,
		placeholder = 'Enter text...',
		action,
		fieldName = 'description',
		multiline = false,
		emptyText = 'No description'
	}: Props = $props();

	let isEditing = $state(false);
	let editValue = $state('');
	let isSubmitting = $state(false);

	function startEditing() {
		editValue = value ?? '';
		isEditing = true;
	}

	// Reset editValue when value prop changes (e.g., after successful save)
	$effect(() => {
		if (!isEditing) {
			editValue = value ?? '';
		}
	});

	function cancelEditing() {
		editValue = value ?? '';
		isEditing = false;
	}
</script>

{#if isEditing}
	<form
		method="POST"
		{action}
		use:enhance={() => {
			isSubmitting = true;
			return async ({ result, update }) => {
				isSubmitting = false;
				if (result.type === 'success') {
					isEditing = false;
					await update();
				}
			};
		}}
		class="edit-form"
	>
		{#if multiline}
			<textarea
				name={fieldName}
				bind:value={editValue}
				{placeholder}
				rows="3"
				disabled={isSubmitting}
				class="edit-input"
			></textarea>
		{:else}
			<input
				type="text"
				name={fieldName}
				bind:value={editValue}
				{placeholder}
				disabled={isSubmitting}
				class="edit-input"
			/>
		{/if}
		<div class="edit-actions">
			<button type="submit" class="save-button" disabled={isSubmitting}>
				{isSubmitting ? 'Saving...' : 'Save'}
			</button>
			<button type="button" class="cancel-button" onclick={cancelEditing} disabled={isSubmitting}>
				Cancel
			</button>
		</div>
	</form>
{:else}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="display-container" onclick={startEditing}>
		{#if value}
			<span class="display-text">{value}</span>
		{:else}
			<span class="empty-text">{emptyText}</span>
		{/if}
		<button class="edit-button" onclick={startEditing} aria-label="Edit">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="14"
				height="14"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
				<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
			</svg>
		</button>
	</div>
{/if}

<style>
	.display-container {
		display: flex;
		align-items: flex-start;
		gap: 0.5rem;
		cursor: pointer;
		padding: 0.25rem;
		margin: -0.25rem;
		border-radius: 0.25rem;
		transition: background-color 0.15s;
	}

	.display-container:hover {
		background-color: #f1f5f9;
	}

	.display-text {
		font-size: 0.875rem;
		color: #64748b;
		line-height: 1.5;
	}

	.empty-text {
		font-size: 0.875rem;
		color: #94a3b8;
		font-style: italic;
	}

	.edit-button {
		flex-shrink: 0;
		padding: 0.25rem;
		background: none;
		border: none;
		color: #94a3b8;
		cursor: pointer;
		opacity: 0;
		transition: opacity 0.15s;
	}

	.display-container:hover .edit-button {
		opacity: 1;
	}

	.edit-button:hover {
		color: #3b82f6;
	}

	.edit-form {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.edit-input {
		width: 100%;
		padding: 0.5rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		box-sizing: border-box;
		font-family: inherit;
	}

	.edit-input:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	textarea.edit-input {
		resize: vertical;
		min-height: 60px;
	}

	.edit-actions {
		display: flex;
		gap: 0.5rem;
	}

	.save-button {
		padding: 0.375rem 0.75rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
	}

	.save-button:hover:not(:disabled) {
		background: #2563eb;
	}

	.save-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.cancel-button {
		padding: 0.375rem 0.75rem;
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
		border-radius: 0.25rem;
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
	}

	.cancel-button:hover:not(:disabled) {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	.cancel-button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}
</style>
