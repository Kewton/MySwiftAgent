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
import { createSecretManagerFromEnv } from '../shared/context/SecretManager.js';
import { AnthropicClient } from '../taskflowGeneratorAgent/llm/clients/AnthropicClient.js';
import { createTaskFlowRoutes } from '../taskflowEngine/api/routes.js';
import type { HandlerDependencies as TaskFlowHandlerDependencies } from '../taskflowEngine/api/handlers.js';
import { createTaskFlowEngine } from '../taskflowEngine/TaskFlowEngine.js';
import { createSchemaValidator } from '../taskflowEngine/validator/SchemaValidator.js';
// Issue #372: CapabilityExecutor integration imports
import {
  createCapabilityRegistry,
  createCapabilityLoader,
  createEndpointConfigManager,
  createURLResolver,
} from '../capabilityManagement/index.js';
import { createCapabilityExecutor } from '../taskflowEngine/nodes/CapabilityExecutor.js';

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
    capabilities: string;
  };
}

/**
 * Create generator dependencies
 *
 * Note: This function creates dependencies for the TaskFlow Generator API handlers.
 * The handlers will create WorkflowGenerator and BatchProcessor internally.
 */
async function createGeneratorDependencies(): Promise<HandlerDependencies> {
  // Create workflow registry for registration
  const registry = new WorkflowRegistry();

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
  };
}

/**
 * Create TaskFlow Engine dependencies
 *
 * Issue #372: Now includes CapabilityExecutor for capability_id based API execution.
 * Creates all required dependencies for TaskFlow Engine API handlers.
 *
 * @param registry - WorkflowRegistry for workflow management
 * @param capabilitiesBasePath - Base path for capability configuration files
 */
async function createTaskFlowEngineDependencies(
  registry: WorkflowRegistry,
  capabilitiesBasePath: string
): Promise<TaskFlowHandlerDependencies> {
  // Issue #372: Create capability management dependencies
  // 1. Create CapabilityRegistry
  const capabilityRegistry = createCapabilityRegistry();

  // 2. Create CapabilityLoader and load capabilities
  const capabilityLoader = createCapabilityLoader(capabilitiesBasePath, capabilityRegistry);
  const loadResult = await capabilityLoader.loadProject('default_project');

  // Log capability loading result
  if (loadResult.hasCapabilities) {
    console.log(
      `[TaskFlowEngine] Loaded ${loadResult.successful.length} capabilities for default_project`
    );
    if (loadResult.failed.length > 0) {
      console.warn(
        `[TaskFlowEngine] Failed to load ${loadResult.failed.length} capabilities:`,
        loadResult.failed.map((f) => f.file)
      );
    }
  } else {
    console.warn('[TaskFlowEngine] No capabilities loaded for default_project');
  }

  // 3. Create EndpointConfigManager for URL resolution
  const endpointConfigManager = createEndpointConfigManager(capabilitiesBasePath);

  // 4. Create URLResolver
  const urlResolver = createURLResolver(endpointConfigManager, 'default_project');

  // 5. Create CapabilityExecutor
  const capabilityExecutor = createCapabilityExecutor(capabilityRegistry, urlResolver);

  // 6. Create TaskFlowEngine with CapabilityExecutor
  const executor = createTaskFlowEngine({
    capabilityExecutor,
  });

  // Create schema validator
  const validator = createSchemaValidator();

  return {
    registry,
    executor,
    validator,
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
        { path: '/api/v1/generator', description: 'TaskFlow Generator Agent API' },
        { path: '/api/v1/capabilities', description: 'Capability Management API' },
      ],
    });
  });

  // TaskFlow Generator routes - Issue #364 integration
  const generatorDeps = await createGeneratorDependencies();
  const generatorApi = createGeneratorApi(generatorDeps);
  app.route('/', generatorApi);

  // TaskFlow Engine routes - Issue #363 integration
  // Issue #372: Share registry and load capabilities for capability_id based execution
  // Capabilities are loaded from config/capabilities directory
  const capabilitiesBasePath = path.resolve(process.cwd(), 'config', 'capabilities');
  const taskFlowDeps = await createTaskFlowEngineDependencies(generatorDeps.registry, capabilitiesBasePath);
  const taskFlowRoutes = createTaskFlowRoutes(taskFlowDeps);
  app.route('/api/v1/taskflow', taskFlowRoutes);

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
