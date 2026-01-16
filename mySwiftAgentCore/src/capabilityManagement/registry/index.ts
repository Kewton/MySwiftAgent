/**
 * Registry module exports
 *
 * Issue #365: Capability registry and project management
 */

export {
  CapabilityRegistry,
  createCapabilityRegistry,
  type RegistryStats,
} from './CapabilityRegistry.js';

export {
  ProjectManager,
  createProjectManager,
  type ProjectInfo,
  type ProjectUpdate,
  type ProjectStats,
} from './ProjectManager.js';
