/**
 * Capability Loader Module
 *
 * Issue #365: YAML loading for capability definitions
 * Issue #372: Capability loading from YAML files for registry
 *
 * Exports:
 * - YamlLoader class (Issue #365)
 * - CapabilitySanitizer class (Issue #365)
 * - CapabilityLoader class (Issue #372)
 * - Factory functions
 */

// Issue #365: YAML loading and sanitization
export {
  YamlLoader,
  CapabilitySanitizer,
  createYamlLoader,
  createSanitizer,
  type YamlLoaderConfig,
  type LoaderStrategy,
} from './YamlLoader.js';

// Issue #372: Capability loading for registry
export {
  CapabilityLoader,
  createCapabilityLoader,
  type CapabilityLoaderOptions,
} from './CapabilityLoader.js';
