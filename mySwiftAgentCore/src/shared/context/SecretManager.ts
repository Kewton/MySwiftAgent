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
 *
 * Compatible with MyVault API (same pattern as graphAiServer)
 */
export interface MyVaultConfig {
  baseUrl: string;
  serviceName: string;
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
   *
   * Uses MyVault API compatible with graphAiServer pattern:
   * - Endpoint: /api/secrets/{project}/{key}
   * - Headers: X-Service, X-Token
   */
  private async getFromMyVault(key: string): Promise<string | undefined> {
    const { baseUrl, serviceName, serviceToken, project } = this.config.myVault!;

    const url = new URL(
      `/api/secrets/${encodeURIComponent(project ?? 'default')}/${encodeURIComponent(key)}`,
      baseUrl
    );

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'X-Service': serviceName,
        'X-Token': serviceToken,
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
 *
 * Required environment variables for MyVault:
 * - MYVAULT_ENABLED: 'true' to enable MyVault
 * - MYVAULT_BASE_URL: MyVault server URL (default: http://localhost:8003)
 * - MYVAULT_SERVICE_NAME: Service name for X-Service header (default: mySwiftAgentCore)
 * - MYVAULT_SERVICE_TOKEN: Token for X-Token header
 * - MYVAULT_DEFAULT_PROJECT: Default project name (default: default)
 */
export function createSecretManagerFromEnv(): SecretManager {
  const myVaultEnabled = process.env['MYVAULT_ENABLED'] === 'true';

  if (myVaultEnabled) {
    return new SecretManager({
      myVault: {
        baseUrl: process.env['MYVAULT_BASE_URL'] ?? 'http://localhost:8003',
        serviceName: process.env['MYVAULT_SERVICE_NAME'] ?? 'mySwiftAgentCore',
        serviceToken: process.env['MYVAULT_SERVICE_TOKEN'] ?? '',
        project: process.env['MYVAULT_DEFAULT_PROJECT'] ?? 'default',
      },
      fallbackToEnv: true,
    });
  }

  return new SecretManager({
    fallbackToEnv: true,
  });
}
