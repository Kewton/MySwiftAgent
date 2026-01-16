/**
 * SecretManager - Secret management for workflow execution
 *
 * Manages secrets for workflow execution, with support for
 * MyVault integration and local fallback.
 */

/**
 * Secret provider interface
 */
export interface SecretProvider {
  get(key: string): Promise<string | undefined>;
  set?(key: string, value: string): Promise<void>;
  delete?(key: string): Promise<void>;
}

/**
 * MyVault client configuration
 */
export interface MyVaultConfig {
  baseUrl: string;
  serviceToken: string;
  project?: string;
}

/**
 * SecretManager configuration
 */
export interface SecretManagerConfig {
  myVault?: MyVaultConfig;
  fallbackToEnv?: boolean;
}

/**
 * SecretManager class - manages secrets for workflows
 */
export class SecretManager implements SecretProvider {
  private readonly config: SecretManagerConfig;
  private readonly cache: Map<string, { value: string; expiresAt: number }>;
  private readonly cacheTTL: number = 300000; // 5 minutes

  constructor(config: SecretManagerConfig = {}) {
    this.config = config;
    this.cache = new Map();
  }

  /**
   * Get a secret value
   */
  async get(key: string): Promise<string | undefined> {
    // Check cache first
    const cached = this.cache.get(key);
    if (cached && cached.expiresAt > Date.now()) {
      return cached.value;
    }

    // Try MyVault if configured
    if (this.config.myVault) {
      try {
        const value = await this.getFromMyVault(key);
        if (value !== undefined) {
          this.cacheSecret(key, value);
          return value;
        }
      } catch {
        // Fall through to environment fallback
      }
    }

    // Fallback to environment variables
    if (this.config.fallbackToEnv !== false) {
      const envValue = process.env[key];
      if (envValue !== undefined) {
        return envValue;
      }
    }

    return undefined;
  }

  /**
   * Get a secret from MyVault
   */
  private async getFromMyVault(key: string): Promise<string | undefined> {
    const { baseUrl, serviceToken, project } = this.config.myVault!;

    const url = new URL(
      `/api/v1/secrets/${encodeURIComponent(project ?? 'default')}/${encodeURIComponent(key)}`,
      baseUrl
    );

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${serviceToken}`,
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return undefined;
      }
      throw new Error(`MyVault error: ${response.status} ${response.statusText}`);
    }

    const data = (await response.json()) as { value?: string };
    return data.value;
  }

  /**
   * Cache a secret value
   */
  private cacheSecret(key: string, value: string): void {
    this.cache.set(key, {
      value,
      expiresAt: Date.now() + this.cacheTTL,
    });
  }

  /**
   * Clear the secret cache
   */
  clearCache(): void {
    this.cache.clear();
  }

  /**
   * Check if MyVault is configured
   */
  isMyVaultEnabled(): boolean {
    return this.config.myVault !== undefined;
  }

  /**
   * Get the configured MyVault base URL
   */
  getMyVaultBaseUrl(): string | undefined {
    return this.config.myVault?.baseUrl;
  }
}

/**
 * Factory function to create SecretManager
 */
export function createSecretManager(config?: SecretManagerConfig): SecretManager {
  return new SecretManager(config);
}

/**
 * Create SecretManager from environment variables
 */
export function createSecretManagerFromEnv(): SecretManager {
  const myVaultEnabled = process.env['MYVAULT_ENABLED'] === 'true';

  if (myVaultEnabled) {
    return new SecretManager({
      myVault: {
        baseUrl: process.env['MYVAULT_BASE_URL'] ?? 'http://localhost:8003',
        serviceToken: process.env['MYVAULT_SERVICE_TOKEN'] ?? '',
        project: process.env['MYVAULT_DEFAULT_PROJECT'],
      },
      fallbackToEnv: true,
    });
  }

  return new SecretManager({
    fallbackToEnv: true,
  });
}
