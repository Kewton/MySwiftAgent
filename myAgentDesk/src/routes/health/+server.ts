import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

/**
 * Health Check Endpoint
 *
 * Purpose: Docker health check and monitoring
 *
 * Response:
 * - 200 OK: Application is healthy
 * - 503 Service Unavailable: Application has issues
 */
export const GET: RequestHandler = async () => {
	try {
		// Basic health check - can be extended with:
		// - Database connectivity check
		// - External API availability check
		// - Memory usage check
		// - Disk space check

		const health = {
			status: 'healthy',
			timestamp: new Date().toISOString(),
			uptime: process.uptime(),
			service: 'myAgentDesk',
			version: '0.1.0',
			environment: process.env.NODE_ENV || 'development'
		};

		return json(health, { status: 200 });
	} catch (error) {
		const unhealthy = {
			status: 'unhealthy',
			timestamp: new Date().toISOString(),
			error: error instanceof Error ? error.message : 'Unknown error'
		};

		return json(unhealthy, { status: 503 });
	}
};
