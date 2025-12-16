<!--
  CreateProjectModal Component
  Issue #288: Project screens implementation

  Modal dialog for creating a new project.
-->
<script lang="ts">
	interface Props {
		isOpen: boolean;
		onClose?: () => void;
		onSubmit?: (data: { name: string; description: string }) => void;
	}

	let { isOpen, onClose, onSubmit }: Props = $props();

	let name = $state('');
	let description = $state('');

	function handleSubmit(event: Event) {
		event.preventDefault();
		if (onSubmit) {
			onSubmit({ name, description });
		}
	}

	function handleCancel() {
		name = '';
		description = '';
		if (onClose) {
			onClose();
		}
	}
</script>

{#if isOpen}
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<div class="modal-backdrop" onclick={handleCancel} role="presentation">
		<!-- svelte-ignore a11y_interactive_supports_focus -->
		<!-- svelte-ignore a11y_click_events_have_key_events -->
		<div
			class="modal-content"
			onclick={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
		>
			<div class="modal-header">
				<h2 id="modal-title">New Project</h2>
				<button class="close-button" onclick={handleCancel} aria-label="Close">
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

			<form onsubmit={handleSubmit}>
				<div class="form-group">
					<label for="project-name">Project Name</label>
					<input
						id="project-name"
						type="text"
						bind:value={name}
						placeholder="Enter project name"
						required
					/>
				</div>

				<div class="form-group">
					<label for="project-description">Description</label>
					<textarea
						id="project-description"
						bind:value={description}
						placeholder="Enter project description (optional)"
						rows="3"
					></textarea>
				</div>

				<div class="modal-actions">
					<button type="button" class="cancel-button" onclick={handleCancel}> Cancel </button>
					<button type="submit" class="submit-button"> Create Project </button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 50;
	}

	.modal-content {
		background: white;
		border-radius: 0.5rem;
		padding: 1.5rem;
		width: 100%;
		max-width: 480px;
		box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
	}

	.modal-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.modal-header h2 {
		font-size: 1.25rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0;
	}

	.close-button {
		background: none;
		border: none;
		color: #64748b;
		cursor: pointer;
		padding: 0.25rem;
	}

	.close-button:hover {
		color: #1e293b;
	}

	.form-group {
		margin-bottom: 1rem;
	}

	.form-group label {
		display: block;
		font-size: 0.875rem;
		font-weight: 500;
		color: #374151;
		margin-bottom: 0.5rem;
	}

	.form-group input,
	.form-group textarea {
		width: 100%;
		padding: 0.5rem 0.75rem;
		border: 1px solid #d1d5db;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		box-sizing: border-box;
	}

	.form-group input:focus,
	.form-group textarea:focus {
		outline: none;
		border-color: #3b82f6;
		box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
	}

	.form-group textarea {
		resize: vertical;
	}

	.modal-actions {
		display: flex;
		justify-content: flex-end;
		gap: 0.75rem;
		margin-top: 1.5rem;
	}

	.cancel-button {
		padding: 0.5rem 1rem;
		background: white;
		color: #64748b;
		border: 1px solid #e2e8f0;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.cancel-button:hover {
		border-color: #cbd5e1;
		color: #1e293b;
	}

	.submit-button {
		padding: 0.5rem 1rem;
		background: #3b82f6;
		color: white;
		border: none;
		border-radius: 0.375rem;
		font-size: 0.875rem;
		font-weight: 500;
		cursor: pointer;
	}

	.submit-button:hover {
		background: #2563eb;
	}
</style>
