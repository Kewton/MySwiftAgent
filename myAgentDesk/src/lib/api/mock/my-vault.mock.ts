/**
 * @file MyVaultClient mock implementation
 * @description Mock client for MyVault API
 */

import { ok, type Result } from '../result';
import { type ApiError } from '../errors';
import type {
	MyVaultClient,
	SecretResponse,
	CreateSecretRequest,
	UpdateSecretRequest
} from '../clients/my-vault';

/**
 * Mock data for secrets
 */
const mockSecrets: SecretResponse[] = [
	{
		key: 'ANTHROPIC_API_KEY',
		value: 'sk-ant-mock-xxx',
		project: 'default_project',
		description: 'Claude API Key',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	},
	{
		key: 'GEMINI_API_KEY',
		value: 'AIza-mock-xxx',
		project: 'default_project',
		description: 'Google Gemini API Key',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	},
	{
		key: 'OPENAI_API_KEY',
		value: 'sk-mock-xxx',
		project: 'default_project',
		description: 'OpenAI API Key',
		created_at: new Date().toISOString(),
		updated_at: new Date().toISOString()
	}
];

/**
 * Mock MyVault client
 */
export class MyVaultClientMock implements Partial<MyVaultClient> {
	private secrets: SecretResponse[] = [...mockSecrets];

	async getSecret(project: string, key: string): Promise<Result<SecretResponse, ApiError>> {
		await this.delay(50);
		const secret = this.secrets.find((s) => s.project === project && s.key === key);
		if (secret) {
			return ok(secret);
		}
		return ok({
			key,
			project,
			value: undefined
		});
	}

	async listSecrets(): Promise<Result<SecretResponse[], ApiError>> {
		await this.delay(50);
		// Return without values for security
		return ok(
			this.secrets.map((s) => ({
				key: s.key,
				project: s.project,
				description: s.description,
				created_at: s.created_at,
				updated_at: s.updated_at
			}))
		);
	}

	async createSecret(request: CreateSecretRequest): Promise<Result<SecretResponse, ApiError>> {
		await this.delay(100);
		const newSecret: SecretResponse = {
			key: request.key,
			value: request.value,
			project: request.project,
			description: request.description,
			created_at: new Date().toISOString(),
			updated_at: new Date().toISOString()
		};
		this.secrets.push(newSecret);
		return ok(newSecret);
	}

	async updateSecret(
		project: string,
		key: string,
		request: UpdateSecretRequest
	): Promise<Result<SecretResponse, ApiError>> {
		await this.delay(50);
		const idx = this.secrets.findIndex((s) => s.project === project && s.key === key);
		if (idx >= 0) {
			this.secrets[idx] = {
				...this.secrets[idx],
				value: request.value,
				description: request.description ?? this.secrets[idx].description,
				updated_at: new Date().toISOString()
			};
			return ok(this.secrets[idx]);
		}
		return ok({
			key,
			project,
			value: request.value,
			description: request.description
		});
	}

	async deleteSecret(_project: string, _key: string): Promise<Result<void, ApiError>> {
		await this.delay(50);
		return ok(undefined);
	}

	async getDefaultProject(): Promise<Result<{ project: string }, ApiError>> {
		await this.delay(50);
		return ok({ project: 'default_project' });
	}

	private delay(ms: number): Promise<void> {
		return new Promise((resolve) => setTimeout(resolve, ms));
	}
}
