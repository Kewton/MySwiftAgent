/**
 * SecretsList Component Tests
 * Issue #288: Project screens implementation
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import SecretsList from '../../../src/lib/components/projects/SecretsList.svelte';

describe('SecretsList', () => {
	const mockSecrets = [
		{
			key: 'OPENAI_API_KEY',
			project: 'proj_001',
			description: 'OpenAI API key for LLM operations',
			isConnected: true,
			lastTestedAt: new Date('2024-01-15T10:00:00')
		},
		{
			key: 'DATABASE_URL',
			project: 'proj_001',
			description: 'Database connection string',
			isConnected: false,
			lastTestedAt: undefined
		}
	];

	it('should render secret keys', () => {
		render(SecretsList, { props: { secrets: mockSecrets } });
		expect(screen.getByText('OPENAI_API_KEY')).toBeTruthy();
		expect(screen.getByText('DATABASE_URL')).toBeTruthy();
	});

	it('should show connection status', () => {
		render(SecretsList, { props: { secrets: mockSecrets } });
		expect(screen.getByText('Connected')).toBeTruthy();
		expect(screen.getByText('Not Connected')).toBeTruthy();
	});

	it('should display descriptions', () => {
		render(SecretsList, { props: { secrets: mockSecrets } });
		expect(screen.getByText('OpenAI API key for LLM operations')).toBeTruthy();
		expect(screen.getByText('Database connection string')).toBeTruthy();
	});

	it('should show empty state when no secrets', () => {
		render(SecretsList, { props: { secrets: [] } });
		expect(screen.getByText(/No secrets configured/i)).toBeTruthy();
	});

	it('should render test connection button', () => {
		render(SecretsList, { props: { secrets: mockSecrets } });
		const buttons = screen.getAllByRole('button');
		expect(buttons.length).toBeGreaterThan(0);
	});
});
