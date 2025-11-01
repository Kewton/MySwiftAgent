const DEFAULT_API_BASE = 'http://localhost:8104/aiagent-api/v1';

function sanitizeBaseUrl(url: string): string {
	return url.replace(/\/$/, '');
}

function readEnvBaseUrl(): string | undefined {
	const env = import.meta.env ?? {};
	const explicit =
		(env.PUBLIC_AGENT_API_BASE as string | undefined) ||
		(env.VITE_AGENT_API_BASE as string | undefined);
	if (!explicit) return undefined;
	return sanitizeBaseUrl(explicit);
}

export function getApiBase(): string {
	try {
		const envBase = readEnvBaseUrl();
		return envBase || DEFAULT_API_BASE;
	} catch (error) {
		console.warn('Failed to resolve API base URL, falling back to default.', error);
		return DEFAULT_API_BASE;
	}
}

export { DEFAULT_API_BASE };
