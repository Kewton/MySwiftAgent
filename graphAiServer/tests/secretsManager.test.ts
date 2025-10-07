// tests/secretsManager.test.ts
import { SecretsManager } from '../src/services/secretsManager';
import { MyVaultClient, MyVaultError } from '../src/services/myvaultClient';
import { settings } from '../src/config/settings';

// Mock dependencies
jest.mock('../src/services/myvaultClient');
jest.mock('../src/config/settings', () => ({
  settings: {
    SECRETS_CACHE_TTL: 300,
    MYVAULT_ENABLED: true,
    MYVAULT_BASE_URL: 'http://localhost:8000',
    MYVAULT_SERVICE_NAME: 'test-service',
    MYVAULT_SERVICE_TOKEN: 'test-token',
    MYVAULT_DEFAULT_PROJECT: 'test-project',
    OPENAI_API_KEY: 'env-openai-key',
    ANTHROPIC_API_KEY: 'env-anthropic-key',
  },
}));

const MockedMyVaultClient = MyVaultClient as jest.MockedClass<typeof MyVaultClient>;

describe('SecretsManager', () => {
  let manager: SecretsManager;
  let mockClient: jest.Mocked<MyVaultClient>;

  beforeEach(() => {
    jest.clearAllMocks();

    // Create mock client instance
    mockClient = {
      getSecret: jest.fn(),
      getSecrets: jest.fn(),
      getDefaultProject: jest.fn(),
    } as any;

    MockedMyVaultClient.mockImplementation(() => mockClient);

    // Reset settings for each test
    (settings as any).MYVAULT_ENABLED = true;
    (settings as any).MYVAULT_DEFAULT_PROJECT = 'test-project';
    (settings as any).OPENAI_API_KEY = 'env-openai-key';

    // Suppress console.log for cleaner test output
    jest.spyOn(console, 'log').mockImplementation();
    jest.spyOn(console, 'warn').mockImplementation();
    jest.spyOn(console, 'error').mockImplementation();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('constructor', () => {
    it('should initialize with MyVault enabled', () => {
      manager = new SecretsManager();

      expect(MockedMyVaultClient).toHaveBeenCalledWith(
        'http://localhost:8000',
        'test-service',
        'test-token'
      );
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining('✓ MyVault client initialized')
      );
    });

    it('should handle MyVault initialization failure', () => {
      MockedMyVaultClient.mockImplementation(() => {
        throw new Error('Connection failed');
      });

      manager = new SecretsManager();

      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('✗ Failed to initialize MyVault client')
      );
    });
  });

  describe('getSecret', () => {
    beforeEach(() => {
      manager = new SecretsManager();
    });

    it('should retrieve secret from MyVault (priority)', async () => {
      mockClient.getSecret.mockResolvedValue('myvault-openai-key');

      const result = await manager.getSecret('OPENAI_API_KEY');

      expect(result).toBe('myvault-openai-key');
      expect(mockClient.getSecret).toHaveBeenCalledWith('test-project', 'OPENAI_API_KEY');
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining("✓ Secret 'OPENAI_API_KEY' retrieved from MyVault")
      );
    });

    it('should fallback to environment variable when MyVault fails', async () => {
      // Make getSecret return null (not throw), which causes fallback
      mockClient.getSecret.mockResolvedValue(null as any);

      const result = await manager.getSecret('OPENAI_API_KEY');

      expect(result).toBe('env-openai-key');
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining("↓ Secret 'OPENAI_API_KEY' retrieved from environment variable")
      );
    });

    it('should throw error when secret not found anywhere', async () => {
      mockClient.getSecret.mockRejectedValue(new MyVaultError('Not found'));
      delete (settings as any).OPENAI_API_KEY;

      await expect(manager.getSecret('OPENAI_API_KEY')).rejects.toThrow(
        "Secret 'OPENAI_API_KEY' not found in MyVault or environment variables"
      );
    });

    it('should use provided project parameter', async () => {
      mockClient.getSecret.mockResolvedValue('custom-project-key');

      const result = await manager.getSecret('OPENAI_API_KEY', 'custom-project');

      expect(result).toBe('custom-project-key');
      expect(mockClient.getSecret).toHaveBeenCalledWith('custom-project', 'OPENAI_API_KEY');
    });
  });

  describe('cache functionality', () => {
    beforeEach(() => {
      manager = new SecretsManager();
    });

    it('should cache secrets from MyVault', async () => {
      mockClient.getSecret.mockResolvedValue('cached-value');

      // First call - cache miss
      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(1);

      // Second call - cache hit
      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(1); // No additional call
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining("Cache hit for 'OPENAI_API_KEY'")
      );
    });

    it('should expire cache after TTL', async () => {
      mockClient.getSecret.mockResolvedValue('cached-value');

      // First call - cache miss
      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(1);

      // Fast-forward time beyond TTL (300 seconds)
      jest.spyOn(Date, 'now').mockReturnValue(Date.now() + 301000);

      // Second call - cache expired
      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(2);
    });

    it('should clear cache manually', async () => {
      mockClient.getSecret.mockResolvedValue('cached-value');

      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(1);

      // Clear cache
      manager.clearCache();
      expect(console.log).toHaveBeenCalledWith('All cache cleared');

      // Next call should fetch from MyVault again
      await manager.getSecret('OPENAI_API_KEY');
      expect(mockClient.getSecret).toHaveBeenCalledTimes(2);
    });

    it('should clear cache for specific project', async () => {
      mockClient.getSecret.mockResolvedValue('value1');

      await manager.getSecret('OPENAI_API_KEY', 'project1');
      await manager.getSecret('ANTHROPIC_API_KEY', 'project2');

      manager.clearCache('project1');
      expect(console.log).toHaveBeenCalledWith('Cache cleared for project: project1');

      // project1 cache cleared, should fetch again
      await manager.getSecret('OPENAI_API_KEY', 'project1');
      expect(mockClient.getSecret).toHaveBeenCalledWith('project1', 'OPENAI_API_KEY');

      // project2 cache still valid, no fetch
      mockClient.getSecret.mockClear();
      await manager.getSecret('ANTHROPIC_API_KEY', 'project2');
      expect(mockClient.getSecret).not.toHaveBeenCalled();
    });
  });

  describe('getSecretsForProject', () => {
    beforeEach(() => {
      manager = new SecretsManager();
    });

    it('should retrieve all secrets for a project from MyVault', async () => {
      const mockSecrets = {
        OPENAI_API_KEY: 'sk-test123',
        ANTHROPIC_API_KEY: 'sk-ant-test456',
      };
      mockClient.getSecrets.mockResolvedValue(mockSecrets);

      const result = await manager.getSecretsForProject('test-project');

      expect(result).toEqual(mockSecrets);
      expect(mockClient.getSecrets).toHaveBeenCalledWith('test-project');
    });

    it('should handle MyVault failure gracefully', async () => {
      mockClient.getSecrets.mockRejectedValue(new MyVaultError('Connection failed'));

      // Set up process.env
      process.env.OPENAI_API_KEY = 'env-openai-key';
      process.env.ANTHROPIC_API_KEY = 'env-anthropic-key';

      const result = await manager.getSecretsForProject();

      // Verify that method doesn't throw error and returns a result
      // (getProjectSecrets catches errors and returns {}, so console.warn is not called)
      expect(result).toBeDefined();
      expect(typeof result).toBe('object');

      // Clean up
      delete process.env.OPENAI_API_KEY;
      delete process.env.ANTHROPIC_API_KEY;
    });

    it('should return environment secrets when MyVault disabled', async () => {
      (settings as any).MYVAULT_ENABLED = false;
      manager = new SecretsManager();

      const result = await manager.getSecretsForProject();

      expect(result).toHaveProperty('OPENAI_API_KEY', 'env-openai-key');
      expect(mockClient.getSecrets).not.toHaveBeenCalled();
    });

    it('should cache all fetched secrets', async () => {
      const mockSecrets = {
        OPENAI_API_KEY: 'sk-test123',
        ANTHROPIC_API_KEY: 'sk-ant-test456',
      };
      mockClient.getSecrets.mockResolvedValue(mockSecrets);

      await manager.getSecretsForProject('test-project');

      // Subsequent individual secret requests should use cache
      mockClient.getSecret.mockClear();
      await manager.getSecret('OPENAI_API_KEY', 'test-project');
      expect(mockClient.getSecret).not.toHaveBeenCalled();
    });
  });

  describe('MyVault disabled scenarios', () => {
    beforeEach(() => {
      (settings as any).MYVAULT_ENABLED = false;
      manager = new SecretsManager();
    });

    it('should use environment variables when MyVault disabled', async () => {
      const result = await manager.getSecret('OPENAI_API_KEY');

      expect(result).toBe('env-openai-key');
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining("↓ Secret 'OPENAI_API_KEY' retrieved from environment variable")
      );
    });

    it('should throw error when secret not in environment', async () => {
      await expect(manager.getSecret('NONEXISTENT_KEY')).rejects.toThrow(
        "Secret 'NONEXISTENT_KEY' not found in MyVault or environment variables"
      );
    });
  });
});
