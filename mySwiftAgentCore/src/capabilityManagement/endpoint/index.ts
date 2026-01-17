/**
 * Endpoint Management Module
 *
 * Issue #372: Exports for capability API endpoint URL resolution
 */

export {
  // Types
  type EndpointConfig,
  type ApiEndpointsConfig,
  type EndpointAuthConfig,
  type ResolvedEndpoint,
  type ProjectIndexConfig,
  type EndpointConfigManagerOptions,
  type URLResolverOptions,
  type IEndpointConfigManager,
  // Error
  EndpointResolutionError,
  // Schemas
  EndpointConfigSchema,
  ApiEndpointsConfigSchema,
  ProjectIndexConfigSchema,
  EndpointAuthConfigSchema,
  ResolvedEndpointSchema,
} from './types.js';

export {
  EndpointConfigManager,
  createEndpointConfigManager,
} from './EndpointConfigManager.js';

export { URLResolver, createURLResolver } from './URLResolver.js';
