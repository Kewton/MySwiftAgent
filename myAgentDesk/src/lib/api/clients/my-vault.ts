/**
 * @file MyVaultClient implementation
 * @description Client for MyVault API (secret management)
 */

import { ApiClient } from '../base/api-client';
import { type Result } from '../result';
import { type ApiError } from '../errors';

/**
 * MyVault client configuration
 */
export interface MyVaultClientConfig {
	baseUrl: string;
	serviceName: string;
	serviceToken: string;
}

/**
 * Secret response
 */
export interface SecretResponse {
	key: string;
	value?: string;
	project: string;
	description?: string;
	created_at?: string;
	updated_at?: string;
}

/**
 * Create secret request
 */
export interface CreateSecretRequest {
	project: string;
	key: string;
	value: string;
	description?: string;
}

/**
 * Update secret request
 */
export interface UpdateSecretRequest {
	value: string;
	description?: string;
}

/**
 * MyVault API client
 */
export class MyVaultClient extends ApiClient {
	constructor(config: MyVaultClientConfig) {
		super({
			baseUrl: config.baseUrl,
			serviceName: config.serviceName,
			serviceToken: config.serviceToken,
			authType: 'service-token'
		});
	}

	/**
	 * Get a secret by project and key
	 */
	async getSecret(project: string, key: string): Promise<Result<SecretResponse, ApiError>> {
		return this.get<SecretResponse>(`/api/secrets/${project}/${key}`);
	}

	/**
	 * List all secrets
	 */
	async listSecrets(): Promise<Result<SecretResponse[], ApiError>> {
		return this.get<SecretResponse[]>('/api/secrets');
	}

	/**
	 * Create a new secret
	 */
	async createSecret(request: CreateSecretRequest): Promise<Result<SecretResponse, ApiError>> {
		return this.post<SecretResponse>('/api/secrets', request);
	}

	/**
	 * Update a secret
	 */
	async updateSecret(
		project: string,
		key: string,
		request: UpdateSecretRequest
	): Promise<Result<SecretResponse, ApiError>> {
		return this.put<SecretResponse>(`/api/secrets/${project}/${key}`, request);
	}

	/**
	 * Delete a secret
	 */
	async deleteSecret(project: string, key: string): Promise<Result<void, ApiError>> {
		return this.delete(`/api/secrets/${project}/${key}`);
	}

	/**
	 * Get default project info
	 */
	async getDefaultProject(): Promise<Result<{ project: string }, ApiError>> {
		return this.get<{ project: string }>('/projects/default');
	}
}
