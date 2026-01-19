/**
 * API Routes - Main API router configuration
 *
 * Configures all API routes for mySwiftAgentCore.
 */

import { Hono } from 'hono';
import * as path from 'path';
import { createHealthRoutes, createMyVaultCheck, type HealthCheckConfig } from './health.js';
import { createGeneratorApi, type HandlerDependencies } from '../taskflowGeneratorAgent/api/index.js';
import { WorkflowRegistry } from '../taskflowEngine/registry/WorkflowRegistry.js';
import { WorkflowRegistrar } from '../taskflowGeneratorAgent/generator/WorkflowRegistrar.js';
import { WorkflowStorage } from '../taskflowGeneratorAgent/storage/WorkflowStorage.js';
import { createSecretManagerFromEnv } from '../shared/context/SecretManager.js';
import { AnthropicClient } from '../taskflowGeneratorAgent/llm/clients/AnthropicClient.js';
import { createLogger } from '../utils/logger/Logger.js';
import { createTaskFlowRoutes } from '../taskflowEngine/api/routes.js';
import type { HandlerDependencies as TaskFlowHandlerDependencies } from '../taskflowEngine/api/handlers.js';
import { createTaskFlowEngine } from '../taskflowEngine/TaskFlowEngine.js';
import { createSchemaValidator } from '../taskflowEngine/validator/SchemaValidator.js';
// Issue #375: Workflow reload API integration
import { createTaskFlowReloadRoutes, type ReloadHandlerDependencies } from './routes/taskflow-reload.js';
import { createWorkflowReloader } from '../taskflowEngine/loader/WorkflowReloader.js';
import { createWorkflowLoader } from '../taskflowEngine/loader/WorkflowLoader.js';
// Issue #372: CapabilityExecutor integration imports
import {
  createCapabilityRegistry,
  createCapabilityLoader,
  createEndpointConfigManager,
  createURLResolver,
} from '../capabilityManagement/index.js';
import { createCapabilityExecutor } from '../taskflowEngine/nodes/CapabilityExecutor.js';
// Issue #377: SecretAnalyzer integration
import { createSecretAnalyzer } from '../taskflowEngine/analyzer/SecretAnalyzer.js';
import { createDefaultNodeRegistry } from '../taskflowEngine/nodes/index.js';

/**
 * API configuration
 */
export interface ApiConfig {
  serviceName: string;
  version: string;
  startTime: Date;
  myVaultBaseUrl?: string;
}

/**
 * Root API response
 */
interface RootResponse {
  service: string;
  version: string;
  status: string;
  endpoints: {
    health: string;
    taskflowEngine: string;
    taskflowGenerator: string;
    taskflowReload: string;
    capabilities: string;
  };
}

/**
 * Create generator dependencies
 *
 * Note: This function creates dependencies for the TaskFlow Generator API handlers.
 * The handlers will create WorkflowGenerator and BatchProcessor internally.
 *
 * Issue #372: Initialize WorkflowRegistrar to load persisted workflows from disk.
 * Issue #374: Accept CapabilityRegistry for capability enrichment in handlers.
 *
 * @param capabilityRegistry - Optional CapabilityRegistry for enriching capabilities
 */
async function createGeneratorDependencies(
  capabilityRegistry?: import('../capabilityManagement/registry/CapabilityRegistry.js').CapabilityRegistry
): Promise<HandlerDependencies> {
  const logger = createLogger({ name: 'api-routes' });

  // Create workflow registry for registration
  const registry = new WorkflowRegistry();

  // Issue #372: Create WorkflowStorage and Registrar to load persisted workflows
  const storage = new WorkflowStorage();
  const registrar = new WorkflowRegistrar({
    registry,
    storage,
    logger,
  });

  // Initialize registrar to load workflows from disk
  await registrar.initialize();
  logger.info('WorkflowRegistrar initialized with persisted workflows');

  // Get API key from SecretManager (MyVault or environment fallback)
  const secretManager = createSecretManagerFromEnv();
  const apiKey = await secretManager.get('ANTHROPIC_API_KEY') ?? '';

  // Create LLM client (default: Anthropic Claude)
  const llmClient = new AnthropicClient({
    apiKey,
    defaultModel: 'claude-sonnet-4-20250514',
  });

  // Langfuse configuration from environment
  const langfuseConfig = {
    enabled: process.env['LANGFUSE_ENABLED'] === 'true',
    publicKey: process.env['LANGFUSE_PUBLIC_KEY'],
    secretKey: process.env['LANGFUSE_SECRET_KEY'],
    baseUrl: process.env['LANGFUSE_BASE_URL'],
  };

  return {
    llmClient,
    registry,
    langfuseConfig,
    registrar,
    // Issue #374: Include capabilityRegistry for capability enrichment
    capabilityRegistry,
  };
}

/**
 * Create TaskFlow Engine dependencies with shared CapabilityRegistry
 *
 * Issue #374: Uses pre-loaded CapabilityRegistry shared with Generator API.
 * This ensures consistency between capability enrichment and execution.
 *
 * @param registry - WorkflowRegistry for workflow management
 * @param capabilitiesBasePath - Base path for capability configuration files
 * @param capabilityRegistry - Pre-loaded CapabilityRegistry
 * @param secretManager - Optional SecretManager for LLM API key access
 */
async function createTaskFlowEngineDependenciesWithRegistry(
  registry: WorkflowRegistry,
  capabilitiesBasePath: string,
  capabilityRegistry: import('../capabilityManagement/registry/CapabilityRegistry.js').CapabilityRegistry,
  secretManager?: import('../shared/context/SecretManager.js').SecretManager
): Promise<TaskFlowHandlerDependencies> {
  // Issue #374: Use provided capabilityRegistry (already loaded)
  // 1. Create EndpointConfigManager for URL resolution
  const endpointConfigManager = createEndpointConfigManager(capabilitiesBasePath);

  // 2. Create URLResolver
  const urlResolver = createURLResolver(endpointConfigManager, 'default_project');

  // 3. Create CapabilityExecutor with shared registry
  const capabilityExecutor = createCapabilityExecutor(capabilityRegistry, urlResolver);

  // 4. Create TaskFlowEngine with CapabilityExecutor
  const executor = createTaskFlowEngine({
    capabilityExecutor,
  });

  // Create schema validator
  const validator = createSchemaValidator();

  // Issue #377: Create SecretAnalyzer with NodeRegistry
  const nodeRegistry = createDefaultNodeRegistry();
  const secretAnalyzer = createSecretAnalyzer(nodeRegistry);

  return {
    registry,
    executor,
    validator,
    secretManager,
    secretAnalyzer,
  };
}

/**
 * Create main API router
 *
 * Note: This is an async function to support LLM client initialization
 * which requires fetching API keys from MyVault.
 */
export async function createApiRoutes(config: ApiConfig): Promise<Hono> {
  const app = new Hono();

  // Health check configuration
  const healthConfig: HealthCheckConfig = {
    serviceName: config.serviceName,
    version: config.version,
    startTime: config.startTime,
    dependencyChecks: [],
  };

  // Add MyVault dependency check if configured
  if (config.myVaultBaseUrl) {
    healthConfig.dependencyChecks?.push(createMyVaultCheck(config.myVaultBaseUrl));
  }

  // Mount health routes
  const healthRoutes = createHealthRoutes(healthConfig);
  app.route('/', healthRoutes);

  // Root endpoint - API information
  app.get('/', (c) => {
    const response: RootResponse = {
      service: config.serviceName,
      version: config.version,
      status: 'running',
      endpoints: {
        health: '/health',
        taskflowEngine: '/api/v1/taskflow',
        taskflowGenerator: '/api/v1/generator',
        taskflowReload: '/api/v1/taskflow/reload',
        capabilities: '/api/v1/capabilities',
      },
    };
    return c.json(response);
  });

  // API v1 routes
  app.get('/api/v1', (c) => {
    return c.json({
      version: 'v1',
      endpoints: [
        { path: '/api/v1/taskflow', description: 'TaskFlow Engine API' },
        { path: '/api/v1/taskflow/reload', description: 'TaskFlow Reload API (Issue #375)' },
        { path: '/api/v1/generator', description: 'TaskFlow Generator Agent API' },
        { path: '/api/v1/capabilities', description: 'Capability Management API' },
      ],
    });
  });

  // Issue #374: Create CapabilityRegistry early and share between Generator and Engine
  // This ensures that capability enrichment in Generator uses the same registry as Engine
  const capabilitiesBasePath = path.resolve(process.cwd(), 'config', 'capabilities');
  const capabilityRegistry = createCapabilityRegistry();
  const capabilityLoader = createCapabilityLoader(capabilitiesBasePath, capabilityRegistry);

  // Load capabilities for default_project
  const loadResult = await capabilityLoader.loadProject('default_project');
  if (loadResult.hasCapabilities) {
    console.log(
      `[API Routes] Loaded ${loadResult.successful.length} capabilities for default_project`
    );
    if (loadResult.failed.length > 0) {
      console.warn(
        `[API Routes] Failed to load ${loadResult.failed.length} capabilities:`,
        loadResult.failed.map((f) => f.file)
      );
    }
  } else {
    console.warn('[API Routes] No capabilities loaded for default_project');
  }

  // TaskFlow Generator routes - Issue #364 integration
  // Issue #374: Pass capabilityRegistry for capability enrichment
  const generatorDeps = await createGeneratorDependencies(capabilityRegistry);
  const generatorApi = createGeneratorApi(generatorDeps);
  app.route('/', generatorApi);

  // Create SecretManager for LLM API key access
  const secretManager = createSecretManagerFromEnv();

  // TaskFlow Engine routes - Issue #363 integration
  // Issue #372: Share registry and load capabilities for capability_id based execution
  // Issue #374: Reuse capabilityRegistry created above (already loaded)
  const taskFlowDeps = await createTaskFlowEngineDependenciesWithRegistry(
    generatorDeps.registry,
    capabilitiesBasePath,
    capabilityRegistry,
    secretManager
  );
  const taskFlowRoutes = createTaskFlowRoutes(taskFlowDeps);
  app.route('/api/v1/taskflow', taskFlowRoutes);

  // Issue #375: TaskFlow Reload API routes
  // Create WorkflowLoader with same base path as generator storage
  const workflowsBasePath = path.resolve(process.cwd(), 'config', 'taskflow', 'projects');
  const workflowLoader = createWorkflowLoader({ basePath: workflowsBasePath });
  const workflowReloader = createWorkflowReloader(workflowLoader, generatorDeps.registry);

  const reloadDeps: ReloadHandlerDependencies = { reloader: workflowReloader };
  const reloadRoutes = createTaskFlowReloadRoutes(reloadDeps);
  app.route('/api/v1/taskflow', reloadRoutes);

  // Capabilities routes (stub)
  app.get('/api/v1/capabilities', (c) => {
    return c.json({
      service: 'Capability Management',
      status: 'stub',
      message: 'Capability Management API is not yet implemented',
    });
  });

  return app;
}
