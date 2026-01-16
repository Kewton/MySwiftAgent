/**
 * mySwiftAgentCore - Core TypeScript services for MySwiftAgent
 *
 * This is the main entry point for the mySwiftAgentCore service.
 * It provides:
 * - TaskFlow Engine: Workflow execution engine
 * - TaskFlow Generator Agent: AI-powered workflow generation
 * - Capability Management: Agent capability registration and discovery
 *
 * @module mySwiftAgentCore
 */

import { Hono } from 'hono';
import { cors } from 'hono/cors';
import { logger } from 'hono/logger';
import { serve } from '@hono/node-server';
import { createApiRoutes } from './api/routes.js';
import { createAuthMiddleware } from './middleware/auth.js';
import {
  validateSecurityConfig,
  getMissingSecurityEnvVars,
  SECURITY_DEFAULTS,
} from './config/security.js';

// Package info
const SERVICE_NAME = 'mySwiftAgentCore';
const VERSION = '0.1.0';

/**
 * Server configuration
 */
interface ServerConfig {
  port: number;
  host: string;
}

/**
 * Get server configuration from environment
 */
function getServerConfig(): ServerConfig {
  return {
    port: parseInt(process.env['PORT'] ?? '8006', 10),
    host: process.env['HOST'] ?? '0.0.0.0',
  };
}

/**
 * Create the Hono application
 *
 * Note: This is an async function to support LLM client initialization
 * which requires fetching API keys from MyVault.
 */
async function createApp(): Promise<Hono> {
  const app = new Hono();
  const startTime = new Date();

  // Middleware
  app.use('*', logger());

  // CORS configuration
  if (SECURITY_DEFAULTS.corsEnabled) {
    app.use(
      '*',
      cors({
        origin:
          SECURITY_DEFAULTS.corsAllowedOrigins.length > 0
            ? SECURITY_DEFAULTS.corsAllowedOrigins
            : '*',
        allowMethods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        allowHeaders: ['Content-Type', 'Authorization', 'X-API-Token', 'X-Request-ID'],
      })
    );
  }

  // Authentication middleware (skip in development if tokens not set)
  const apiToken = process.env['API_TOKEN'];
  const adminToken = process.env['ADMIN_TOKEN'];

  if (apiToken) {
    app.use(
      '/api/*',
      createAuthMiddleware({
        apiToken,
        adminToken,
        skipPaths: ['/health', '/health/detailed', '/health/ready', '/health/live', '/'],
      })
    );
  }

  // Mount API routes (await since it's async now)
  const apiRoutes = await createApiRoutes({
    serviceName: SERVICE_NAME,
    version: VERSION,
    startTime,
    myVaultBaseUrl: process.env['MYVAULT_BASE_URL'],
  });
  app.route('/', apiRoutes);

  return app;
}

/**
 * Start the server
 */
async function startServer(): Promise<void> {
  // Validate security configuration
  const securityResult = validateSecurityConfig();

  if (!securityResult.valid) {
    const missing = getMissingSecurityEnvVars();
    console.warn(`[WARN] Security configuration incomplete. Missing: ${missing.join(', ')}`);
    console.warn('[WARN] Running in development mode without authentication.');
  }

  if (securityResult.warnings.length > 0) {
    for (const warning of securityResult.warnings) {
      console.warn(`[WARN] ${warning}`);
    }
  }

  const config = getServerConfig();
  const app = await createApp();

  console.log(`
========================================
  ${SERVICE_NAME} v${VERSION}
========================================
  Host: ${config.host}
  Port: ${config.port}
  Environment: ${process.env['NODE_ENV'] ?? 'development'}
========================================
`);

  serve({
    fetch: app.fetch,
    port: config.port,
    hostname: config.host,
  });

  console.log(`[INFO] Server started at http://${config.host}:${config.port}`);
  console.log(`[INFO] Health check: http://${config.host}:${config.port}/health`);
}

// Start server if this is the main module
startServer().catch((error) => {
  console.error('[ERROR] Failed to start server:', error);
  process.exit(1);
});

// Export for testing
export { createApp, startServer, SERVICE_NAME, VERSION };

// Re-export modules
// Note: Named exports to avoid conflicts between modules
export * from './shared/types/index.js';
export * from './shared/context/index.js';
export * from './taskflowEngine/index.js';
// taskflowGeneratorAgent has its own types that may conflict, import separately
export {
  // LLM
  BaseLLMClient,
  LLMParseError,
  LLMValidationError,
  LLMApiError,
  AnthropicClient,
  OpenAIClient,
  GeminiClient,
  LLMClientFactory,
  // Generator
  WorkflowGenerator,
  BatchProcessor,
  WorkflowRegistrar,
  // Recovery
  ErrorHandler,
  RetryStrategy,
  // Prompts
  PromptBuilder,
  // Tracing
  LangfuseIntegration,
  // API
  createGeneratorRoutes,
  createGeneratorApi,
  createBatchGenerationHandler,
  createStatusHandler,
  createHealthHandler,
  // Client
  TaskFlowGeneratorClient,
  TaskFlowGeneratorClientError,
  // Legacy
  TaskFlowGeneratorAgent,
  createTaskFlowGeneratorAgent,
  // Types (with prefixes to avoid conflicts)
  type GenerationRequest,
  type GenerationConstraints,
  type LegacyGenerationResult,
  type TaskFlowGeneratorConfig,
  type ValidationResult as GeneratorValidationResult,
} from './taskflowGeneratorAgent/index.js';
export * from './capabilityManagement/index.js';
