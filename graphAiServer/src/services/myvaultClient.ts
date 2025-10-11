// src/services/myvaultClient.ts
import axios, { AxiosInstance } from 'axios';

export class MyVaultError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'MyVaultError';
  }
}

export class MyVaultClient {
  private client: AxiosInstance;
  private serviceName: string;

  constructor(baseUrl: string, serviceName: string, token: string) {
    this.serviceName = serviceName;
    this.client = axios.create({
      baseURL: baseUrl,
      headers: {
        'X-Service': serviceName,
        'X-Token': token,
      },
      timeout: 5000,
    });
  }

  async getSecret(project: string, key: string): Promise<string> {
    try {
      const response = await this.client.get(`/api/secrets/${project}/${key}`);
      return response.data.value;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
          throw new MyVaultError(`Secret '${key}' not found in project '${project}'`);
        }
        throw new MyVaultError(`Failed to get secret '${key}': HTTP ${error.response?.status}`);
      }
      throw new MyVaultError(`Failed to get secret '${key}': ${String(error)}`);
    }
  }

  async getSecrets(project: string): Promise<Record<string, string>> {
    try {
      const response = await this.client.get(`/api/secrets?project=${project}`);
      const secrets: Record<string, string> = {};
      for (const item of response.data) {
        secrets[item.key] = item.value;
      }
      return secrets;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new MyVaultError(`Failed to get secrets: HTTP ${error.response?.status}`);
      }
      throw new MyVaultError(`Failed to get secrets: ${String(error)}`);
    }
  }

  async getDefaultProject(): Promise<string> {
    try {
      const response = await this.client.get('/projects/default');
      return response.data.name;
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new MyVaultError(`Failed to get default project: HTTP ${error.response?.status}`);
      }
      throw new MyVaultError(`Failed to get default project: ${String(error)}`);
    }
  }
}
