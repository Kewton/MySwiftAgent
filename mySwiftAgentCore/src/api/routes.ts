/**
 * API Routes - Main API router configuration
 *
 * Configures all API routes for mySwiftAgentCore.
 */

import { Hono } from 'hono';
import { createHealthRoutes, createMyVaultCheck, type HealthCheckConfig } from './health.js';

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
 * Create main API router
 */
export function createApiRoutes(config: ApiConfig): Hono {
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

  // TaskFlow Engine routes (stub)
  app.get('/api/v1/taskflow', (c) => {
    return c.json({
      service: 'TaskFlow Engine',
      status: 'stub',
      message: 'TaskFlow Engine API is not yet implemented',
    });
  });

  // TaskFlow Generator routes (stub)
  app.get('/api/v1/generator', (c) => {
    return c.json({
      service: 'TaskFlow Generator Agent',
      status: 'stub',
      message: 'TaskFlow Generator Agent API is not yet implemented',
    });
  });

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
