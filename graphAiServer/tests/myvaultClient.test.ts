// tests/myvaultClient.test.ts
import axios from 'axios';
import { MyVaultClient, MyVaultError } from '../src/services/myvaultClient';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('MyVaultClient', () => {
  let client: MyVaultClient;
  const mockAxiosInstance = {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockedAxios.create.mockReturnValue(mockAxiosInstance as any);

    client = new MyVaultClient(
      'http://localhost:8000',
      'test-service',
      'test-token'
    );
  });

  describe('constructor', () => {
    it('should initialize with correct configuration', () => {
      expect(mockedAxios.create).toHaveBeenCalledWith({
        baseURL: 'http://localhost:8000',
        headers: {
          'X-Service': 'test-service',
          'X-Token': 'test-token',
        },
        timeout: 5000,
      });
    });
  });

  describe('getSecret', () => {
    it('should successfully retrieve a secret', async () => {
      const mockResponse = { data: { value: 'sk-test123' } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await client.getSecret('test-project', 'OPENAI_API_KEY');

      expect(result).toBe('sk-test123');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/api/secrets/test-project/OPENAI_API_KEY'
      );
    });

    it('should throw MyVaultError when secret not found (404)', async () => {
      const error = {
        isAxiosError: true,
        response: { status: 404 },
      };
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(true);

      await expect(
        client.getSecret('test-project', 'NONEXISTENT_KEY')
      ).rejects.toThrow(MyVaultError);

      await expect(
        client.getSecret('test-project', 'NONEXISTENT_KEY')
      ).rejects.toThrow("Secret 'NONEXISTENT_KEY' not found in project 'test-project'");
    });

    it('should throw MyVaultError on HTTP error', async () => {
      const error = {
        isAxiosError: true,
        response: { status: 500 },
      };
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(true);

      await expect(
        client.getSecret('test-project', 'OPENAI_API_KEY')
      ).rejects.toThrow(MyVaultError);

      await expect(
        client.getSecret('test-project', 'OPENAI_API_KEY')
      ).rejects.toThrow("Failed to get secret 'OPENAI_API_KEY': HTTP 500");
    });

    it('should handle non-Axios errors', async () => {
      const error = new Error('Network error');
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(false);

      await expect(
        client.getSecret('test-project', 'OPENAI_API_KEY')
      ).rejects.toThrow(MyVaultError);

      await expect(
        client.getSecret('test-project', 'OPENAI_API_KEY')
      ).rejects.toThrow("Failed to get secret 'OPENAI_API_KEY': Error: Network error");
    });
  });

  describe('getSecrets', () => {
    it('should successfully retrieve all secrets for a project', async () => {
      const mockResponse = {
        data: [
          { key: 'OPENAI_API_KEY', value: 'sk-test123' },
          { key: 'ANTHROPIC_API_KEY', value: 'sk-ant-test456' },
        ],
      };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await client.getSecrets('test-project');

      expect(result).toEqual({
        OPENAI_API_KEY: 'sk-test123',
        ANTHROPIC_API_KEY: 'sk-ant-test456',
      });
      expect(mockAxiosInstance.get).toHaveBeenCalledWith(
        '/api/secrets?project=test-project'
      );
    });

    it('should return empty object when project has no secrets', async () => {
      const mockResponse = { data: [] };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await client.getSecrets('empty-project');

      expect(result).toEqual({});
    });

    it('should throw MyVaultError on HTTP error', async () => {
      const error = {
        isAxiosError: true,
        response: { status: 403 },
      };
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(true);

      await expect(client.getSecrets('test-project')).rejects.toThrow(
        MyVaultError
      );

      await expect(client.getSecrets('test-project')).rejects.toThrow(
        'Failed to get secrets: HTTP 403'
      );
    });
  });

  describe('getDefaultProject', () => {
    it('should successfully retrieve default project', async () => {
      const mockResponse = { data: { name: 'default-project' } };
      mockAxiosInstance.get.mockResolvedValue(mockResponse);

      const result = await client.getDefaultProject();

      expect(result).toBe('default-project');
      expect(mockAxiosInstance.get).toHaveBeenCalledWith('/projects/default');
    });

    it('should throw MyVaultError when default project not found', async () => {
      const error = {
        isAxiosError: true,
        response: { status: 404 },
      };
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(true);

      await expect(client.getDefaultProject()).rejects.toThrow(MyVaultError);

      await expect(client.getDefaultProject()).rejects.toThrow(
        'Failed to get default project: HTTP 404'
      );
    });

    it('should handle non-Axios errors', async () => {
      const error = new Error('Connection timeout');
      mockAxiosInstance.get.mockRejectedValue(error);
      mockedAxios.isAxiosError.mockReturnValue(false);

      await expect(client.getDefaultProject()).rejects.toThrow(MyVaultError);

      await expect(client.getDefaultProject()).rejects.toThrow(
        'Failed to get default project: Error: Connection timeout'
      );
    });
  });
});
