<!--
  Home Page (/)
  Issue #285: SvelteKit Routing Foundation

  Landing page that directs users to the Projects list.
-->
<script lang="ts">
	// Home page - no additional logic needed for MVP
</script>

<div class="home-page">
	<div class="hero">
		<h1>Welcome to MyAgentDesk</h1>
		<p class="subtitle">
			Your personal AI agent workbench for building and managing LLM workflows.
		</p>
		<a href="/projects" class="cta-button">Get Started</a>
	</div>

	<div class="features">
		<div class="feature">
			<h3>Project Management</h3>
			<p>Organize your AI workflows into projects with dedicated workbenches.</p>
		</div>
		<div class="feature">
			<h3>Job Generation</h3>
			<p>Define requirements and automatically generate executable jobs.</p>
		</div>
		<div class="feature">
			<h3>Continuous Improvement</h3>
			<p>Analyze results and iteratively improve your workflows.</p>
		</div>
	</div>
</div>

<style>
	.home-page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 3rem 1rem;
	}

	.hero {
		text-align: center;
		padding: 4rem 0;
	}

	h1 {
		font-size: 2.5rem;
		font-weight: 700;
		color: #1e293b;
		margin: 0 0 1rem;
	}

	.subtitle {
		font-size: 1.125rem;
		color: #64748b;
		margin: 0 0 2rem;
	}

	.cta-button {
		display: inline-block;
		padding: 0.75rem 1.5rem;
		background: #3b82f6;
		color: white;
		text-decoration: none;
		font-weight: 600;
		border-radius: 0.5rem;
		transition: background 0.15s;
	}

	.cta-button:hover {
		background: #2563eb;
	}

	.features {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
		gap: 2rem;
		margin-top: 4rem;
	}

	.feature {
		padding: 1.5rem;
		background: white;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
	}

	.feature h3 {
		font-size: 1.125rem;
		font-weight: 600;
		color: #1e293b;
		margin: 0 0 0.5rem;
	}

	.feature p {
		font-size: 0.875rem;
		color: #64748b;
		margin: 0;
		line-height: 1.5;
	}
</style>
