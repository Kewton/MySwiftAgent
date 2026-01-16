/**
 * Capability API Handlers
 *
 * Issue #365: REST API handlers for capability management
 * Provides endpoints for listing, retrieving, and creating capabilities.
 */

import { Hono } from 'hono';
import { HTTPException } from 'hono/http-exception';
import yaml from 'js-yaml';
import type { Context } from 'hono';
import { CapabilityRegistry } from '../registry/CapabilityRegistry.js';
import { CapabilitySanitizer } from '../loader/YamlLoader.js';
import type {
  CapabilityExtended,
  CapabilityFilterExtended,
  PublicCapability,
} from '../../shared/types/capability.types.js';
import { CapabilityExtendedSchema } from '../../shared/types/capability.types.js';
import type { AuthResult } from '../../middleware/auth.js';

/**
 * Handler dependencies
 */
export interface CapabilityHandlerDependencies {
  registry: CapabilityRegistry;
  sanitizer: CapabilitySanitizer;
}

/**
 * List capabilities response
 */
interface ListCapabilitiesResponse {
  capabilities: PublicCapability[];
  count: number;
  project: string;
}

/**
 * Get capability response
 */
interface GetCapabilityResponse {
  capability: PublicCapability;
}

/**
 * Create capability handlers
 *
 * @param deps - Handler dependencies
 * @returns Hono app with capability routes
 */
export function createCapabilityHandlers(deps: CapabilityHandlerDependencies): Hono {
  const app = new Hono();
  const { registry, sanitizer } = deps;

  /**
   * GET /api/v1/capabilities/yaml
   * Returns capabilities in YAML format
   * Must be defined before /:id to avoid route conflict
   */
  app.get('/api/v1/capabilities/yaml', (c: Context) => {
    const project = c.req.query('project');

    if (!project) {
      return c.json({ error: 'project query parameter is required' }, 400);
    }

    const capabilities = registry.getByProject(project);
    const publicCapabilities = sanitizer.sanitizeMany(capabilities);

    const yamlContent = yaml.dump(publicCapabilities, {
      indent: 2,
      lineWidth: 120,
      noRefs: true,
    });

    return c.text(yamlContent, 200, {
      'Content-Type': 'text/yaml; charset=utf-8',
    });
  });

  /**
   * GET /api/v1/capabilities
   * List capabilities for a project
   */
  app.get('/api/v1/capabilities', (c: Context) => {
    const project = c.req.query('project');

    if (!project) {
      return c.json({ error: 'project query parameter is required' }, 400);
    }

    // Build filter from query params
    const filter: CapabilityFilterExtended = {
      category: c.req.query('category'),
      status: c.req.query('status') as CapabilityFilterExtended['status'],
      searchTerm: c.req.query('search'),
    };

    const tagsParam = c.req.query('tags');
    if (tagsParam) {
      filter.tags = tagsParam.split(',');
    }

    const capabilities = registry.getByProject(project, filter);
    const publicCapabilities = sanitizer.sanitizeMany(capabilities);

    const response: ListCapabilitiesResponse = {
      capabilities: publicCapabilities,
      count: publicCapabilities.length,
      project,
    };

    return c.json(response);
  });

  /**
   * GET /api/v1/capabilities/:id
   * Get a specific capability
   */
  app.get('/api/v1/capabilities/:id', (c: Context) => {
    const project = c.req.query('project');
    const capabilityId = c.req.param('id');

    if (!project) {
      return c.json({ error: 'project query parameter is required' }, 400);
    }

    // Handle "yaml" as id conflict - redirect to yaml endpoint
    if (capabilityId === 'yaml') {
      const capabilities = registry.getByProject(project);
      const publicCapabilities = sanitizer.sanitizeMany(capabilities);

      const yamlContent = yaml.dump(publicCapabilities, {
        indent: 2,
        lineWidth: 120,
        noRefs: true,
      });

      return c.text(yamlContent, 200, {
        'Content-Type': 'text/yaml; charset=utf-8',
      });
    }

    const capability = registry.getCapability(project, capabilityId);

    if (!capability) {
      return c.json({ error: `Capability ${capabilityId} not found` }, 404);
    }

    const publicCapability = sanitizer.sanitize(capability);

    const response: GetCapabilityResponse = {
      capability: publicCapability,
    };

    return c.json(response);
  });

  /**
   * POST /api/v1/capabilities
   * Create a new capability (admin only)
   */
  app.post('/api/v1/capabilities', async (c: Context) => {
    // Check admin privileges
    const auth = c.get('auth') as AuthResult | undefined;

    if (!auth?.authenticated) {
      throw new HTTPException(401, { message: 'Authentication required' });
    }

    if (auth.tokenType !== 'admin') {
      throw new HTTPException(403, { message: 'Admin privileges required' });
    }

    // Parse and validate request body
    const body = await c.req.json();
    const result = CapabilityExtendedSchema.safeParse(body);

    if (!result.success) {
      const errors = result.error.errors.map((e) => `${e.path.join('.')}: ${e.message}`);
      return c.json({ error: 'Invalid capability data', details: errors }, 400);
    }

    const capability: CapabilityExtended = result.data;
    const project = capability.project ?? 'default_project';

    // Register the capability
    registry.registerForProject(project, capability);

    // Return sanitized capability
    const publicCapability = sanitizer.sanitize(capability);

    return c.json({ capability: publicCapability }, 201);
  });

  return app;
}
