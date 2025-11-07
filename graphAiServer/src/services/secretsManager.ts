// src/services/secretsManager.ts
import { settings } from '../config/settings.js';
import { MyVaultClient, MyVaultError } from './myvaultClient.js';

interface CacheEntry {
  value: string;
  timestamp: number;
}

export class SecretsManager {
  private cache: Map<string, Map<string, CacheEntry>> = new Map();
  private cacheTtl: number;
  private myvaultEnabled: boolean;
  private myvaultClient: MyVaultClient | null = null;

  constructor() {
    this.cacheTtl = settings.SECRETS_CACHE_TTL;
    this.myvaultEnabled = settings.MYVAULT_ENABLED;

    if (this.myvaultEnabled) {
      try {
        this.myvaultClient = new MyVaultClient(
          settings.MYVAULT_BASE_URL,
          settings.MYVAULT_SERVICE_NAME,
          settings.MYVAULT_SERVICE_TOKEN
        );
        console.log(`✓ MyVault client initialized: ${settings.MYVAULT_BASE_URL}`);
      } catch (error) {
        console.error(`✗ Failed to initialize MyVault client: ${error}`);
        this.myvaultEnabled = false;
      }
    }
  }

  async getSecret(key: string, project?: string): Promise<string> {
    // 1. Try MyVault first (priority)
    if (this.myvaultEnabled && this.myvaultClient) {
      try {
        const value = await this.getFromMyVault(key, project);
        if (value) {
          console.log(`✓ Secret '${key}' retrieved from MyVault (project: ${project || this.resolveDefaultProject()})`);
          return value;
        }
      } catch (error) {
        console.warn(`MyVault retrieval failed for '${key}': ${error}`);
        // Continue to fallback
      }
    }

    // 2. Fallback to environment variable
    const envValue = process.env[key] || settings[key];
    if (envValue && typeof envValue === 'string') {
      console.log(`↓ Secret '${key}' retrieved from environment variable (fallback)`);
      return envValue;
    }

    // 3. Not found anywhere
    throw new Error(`Secret '${key}' not found in MyVault or environment variables`);
  }

  async getSecretsForProject(project?: string): Promise<Record<string, string>> {
    if (!this.myvaultEnabled || !this.myvaultClient) {
      return this.getAllEnvSecrets();
    }

    try {
      const projectName = project || this.resolveDefaultProject();
      return await this.getProjectSecrets(projectName);
    } catch (error) {
      console.warn(`Failed to get secrets from MyVault, using env vars`);
      return this.getAllEnvSecrets();
    }
  }

  clearCache(project?: string): void {
    if (project) {
      this.cache.delete(project);
      console.log(`Cache cleared for project: ${project}`);
    } else {
      this.cache.clear();
      console.log('All cache cleared');
    }
  }

  private async getFromMyVault(key: string, project?: string): Promise<string | null> {
    if (!this.myvaultClient) {
      return null;
    }

    const projectName = project || this.resolveDefaultProject();
    if (!projectName) {
      throw new MyVaultError('No project specified and no default project found');
    }

    // Check cache
    if (this.isCacheValid(projectName, key)) {
      const cachedValue = this.cache.get(projectName)?.get(key);
      console.log(`Cache hit for '${key}' in project '${projectName}'`);
      return cachedValue!.value;
    }

    // Fetch from MyVault
    try {
      const value = await this.myvaultClient.getSecret(projectName, key);
      this.updateCache(projectName, key, value);
      return value;
    } catch (error) {
      // Secret not found in this project
      return null;
    }
  }

  private async getProjectSecrets(project: string): Promise<Record<string, string>> {
    if (!this.myvaultClient) {
      return {};
    }

    try {
      const secrets = await this.myvaultClient.getSecrets(project);
      // Update cache for all fetched secrets
      for (const [key, value] of Object.entries(secrets)) {
        this.updateCache(project, key, value);
      }
      return secrets;
    } catch (error) {
      return {};
    }
  }

  private resolveDefaultProject(): string {
    // Check env var override
    if (settings.MYVAULT_DEFAULT_PROJECT) {
      return settings.MYVAULT_DEFAULT_PROJECT;
    }

    // In production, should fetch from MyVault API
    // For now, use the setting
    return settings.MYVAULT_DEFAULT_PROJECT;
  }

  private getAllEnvSecrets(): Record<string, string> {
    const secretKeys = [
      'OPENAI_API_KEY',
      'ANTHROPIC_API_KEY',
      'GOOGLE_API_KEY',
      'GROQ_API_KEY',
    ];

    const secrets: Record<string, string> = {};
    for (const key of secretKeys) {
      const value = process.env[key] || settings[key];
      if (value && typeof value === 'string') {
        secrets[key] = value;
      }
    }
    return secrets;
  }

  private isCacheValid(project: string, key: string): boolean {
    const projectCache = this.cache.get(project);
    if (!projectCache) {
      return false;
    }

    const entry = projectCache.get(key);
    if (!entry) {
      return false;
    }

    const age = Date.now() - entry.timestamp;
    return age < this.cacheTtl * 1000;
  }

  private updateCache(project: string, key: string, value: string): void {
    if (!this.cache.has(project)) {
      this.cache.set(project, new Map());
    }

    this.cache.get(project)!.set(key, {
      value,
      timestamp: Date.now(),
    });
  }
}

// Global instance
export const secretsManager = new SecretsManager();
