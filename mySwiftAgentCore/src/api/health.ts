/**
 * Health Check API - Health and readiness endpoints
 *
 * Provides health check endpoints for monitoring and orchestration.
 */

import { Hono } from 'hono';

/**
 * Service dependency status
 */
export interface DependencyStatus {
  name: string;
  status: 'healthy' | 'unhealthy' | 'unknown';
  latencyMs?: number;
  message?: string;
}

/**
 * Health check response
 */
export interface HealthResponse {
  status: 'healthy' | 'unhealthy' | 'degraded';
  service: string;
  version: string;
  timestamp: string;
  uptime: number;
  dependencies?: DependencyStatus[];
}

/**
 * Health check configuration
 */
export interface HealthCheckConfig {
  serviceName: string;
  version: string;
  startTime: Date;
  dependencyChecks?: (() => Promise<DependencyStatus>)[];
}

/**
 * Create health check routes
 */
export function createHealthRoutes(config: HealthCheckConfig): Hono {
  const app = new Hono();

  /**
   * Basic health check - always returns quickly
   * Used by load balancers and container orchestration
   */
  app.get('/health', (c) => {
    const response: HealthResponse = {
      status: 'healthy',
      service: config.serviceName,
      version: config.version,
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - config.startTime.getTime()) / 1000),
    };

    return c.json(response);
  });

  /**
   * Detailed health check - includes dependency status
   * Used for monitoring dashboards
   */
  app.get('/health/detailed', async (c) => {
    const dependencies: DependencyStatus[] = [];
    let overallStatus: 'healthy' | 'unhealthy' | 'degraded' = 'healthy';

    // Check each dependency
    if (config.dependencyChecks) {
      for (const check of config.dependencyChecks) {
        try {
          const status = await check();
          dependencies.push(status);

          if (status.status === 'unhealthy') {
            overallStatus = 'degraded';
          }
        } catch (error) {
          dependencies.push({
            name: 'unknown',
            status: 'unhealthy',
            message: error instanceof Error ? error.message : 'Unknown error',
          });
          overallStatus = 'degraded';
        }
      }
    }

    const response: HealthResponse = {
      status: overallStatus,
      service: config.serviceName,
      version: config.version,
      timestamp: new Date().toISOString(),
      uptime: Math.floor((Date.now() - config.startTime.getTime()) / 1000),
      dependencies,
    };

    const statusCode = overallStatus === 'healthy' ? 200 : overallStatus === 'degraded' ? 200 : 503;
    return c.json(response, statusCode);
  });

  /**
   * Readiness check - returns 200 only when the service is ready to handle requests
   */
  app.get('/health/ready', async (c) => {
    // Check if all critical dependencies are healthy
    if (config.dependencyChecks) {
      for (const check of config.dependencyChecks) {
        try {
          const status = await check();
          if (status.status === 'unhealthy') {
            return c.json(
              {
                ready: false,
                reason: `Dependency ${status.name} is unhealthy: ${status.message}`,
              },
              503
            );
          }
        } catch (error) {
          return c.json(
            {
              ready: false,
              reason: error instanceof Error ? error.message : 'Dependency check failed',
            },
            503
          );
        }
      }
    }

    return c.json({ ready: true });
  });

  /**
   * Liveness check - returns 200 if the service is alive
   */
  app.get('/health/live', (c) => {
    return c.json({ alive: true });
  });

  return app;
}

/**
 * Create a MyVault dependency check
 */
export function createMyVaultCheck(baseUrl: string): () => Promise<DependencyStatus> {
  return async (): Promise<DependencyStatus> => {
    const startTime = Date.now();
    try {
      const response = await fetch(`${baseUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000),
      });

      const latencyMs = Date.now() - startTime;

      if (response.ok) {
        return {
          name: 'myvault',
          status: 'healthy',
          latencyMs,
        };
      }

      return {
        name: 'myvault',
        status: 'unhealthy',
        latencyMs,
        message: `HTTP ${response.status}`,
      };
    } catch (error) {
      return {
        name: 'myvault',
        status: 'unhealthy',
        latencyMs: Date.now() - startTime,
        message: error instanceof Error ? error.message : 'Connection failed',
      };
    }
  };
}
