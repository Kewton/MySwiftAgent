/**
 * WorkflowRegistry - Project-based workflow management
 *
 * Issue #363: Manages workflows organized by project
 * Pattern follows capabilityManagement/CapabilityRegistry
 */

import type { InternalWorkflowDefinition } from '../types/InternalWorkflowDefinition.js';

/**
 * Internal project storage structure
 */
interface ProjectWorkflowStore {
  projectId: string;
  workflows: Map<string, InternalWorkflowDefinition>;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Registry statistics
 */
export interface WorkflowRegistryStats {
  totalProjects: number;
  totalWorkflows: number;
  byProject: Record<string, number>;
}

/**
 * WorkflowRegistry - Manages workflows organized by project
 *
 * Features:
 * - Register workflows for specific projects
 * - Retrieve workflows by project, name, or id
 * - Statistics and reporting
 */
export class WorkflowRegistry {
  private readonly projects: Map<string, ProjectWorkflowStore>;

  constructor() {
    this.projects = new Map();
  }

  /**
   * Register a workflow for a specific project
   *
   * @param projectId - The project identifier
   * @param workflow - The workflow definition to register
   */
  registerForProject(projectId: string, workflow: InternalWorkflowDefinition): void {
    let project = this.projects.get(projectId);

    if (!project) {
      project = {
        projectId,
        workflows: new Map(),
        createdAt: new Date(),
        updatedAt: new Date(),
      };
      this.projects.set(projectId, project);
    }

    project.workflows.set(workflow.id, workflow);
    project.updatedAt = new Date();
  }

  /**
   * Get workflows for a project
   *
   * @param projectId - The project identifier
   * @returns Array of workflows for the project
   */
  getByProject(projectId: string): InternalWorkflowDefinition[] {
    const project = this.projects.get(projectId);

    if (!project) {
      return [];
    }

    return Array.from(project.workflows.values());
  }

  /**
   * Get a specific workflow by project and name
   *
   * @param projectId - The project identifier
   * @param workflowName - The workflow name
   * @returns The workflow if found, undefined otherwise
   */
  getWorkflow(projectId: string, workflowName: string): InternalWorkflowDefinition | undefined {
    const project = this.projects.get(projectId);

    if (!project) {
      return undefined;
    }

    for (const workflow of project.workflows.values()) {
      if (workflow.name === workflowName) {
        return workflow;
      }
    }

    return undefined;
  }

  /**
   * Get a specific workflow by project and id
   *
   * @param projectId - The project identifier
   * @param workflowId - The workflow id
   * @returns The workflow if found, undefined otherwise
   */
  getWorkflowById(projectId: string, workflowId: string): InternalWorkflowDefinition | undefined {
    const project = this.projects.get(projectId);
    return project?.workflows.get(workflowId);
  }

  /**
   * Unregister a workflow from a project
   *
   * @param projectId - The project identifier
   * @param workflowName - The workflow name
   * @returns true if unregistered, false if not found
   */
  unregisterFromProject(projectId: string, workflowName: string): boolean {
    const project = this.projects.get(projectId);

    if (!project) {
      return false;
    }

    for (const [id, workflow] of project.workflows) {
      if (workflow.name === workflowName) {
        project.workflows.delete(id);
        project.updatedAt = new Date();
        return true;
      }
    }

    return false;
  }

  /**
   * List all project IDs
   *
   * @returns Array of project identifiers
   */
  listProjects(): string[] {
    return Array.from(this.projects.keys());
  }

  /**
   * Get registry statistics
   *
   * @returns Statistics about the registry
   */
  getStats(): WorkflowRegistryStats {
    const stats: WorkflowRegistryStats = {
      totalProjects: this.projects.size,
      totalWorkflows: 0,
      byProject: {},
    };

    for (const [projectId, project] of this.projects) {
      const count = project.workflows.size;
      stats.totalWorkflows += count;
      stats.byProject[projectId] = count;
    }

    return stats;
  }

  /**
   * Clear all projects and workflows
   */
  clear(): void {
    this.projects.clear();
  }
}

/**
 * Factory function to create WorkflowRegistry
 */
export function createWorkflowRegistry(): WorkflowRegistry {
  return new WorkflowRegistry();
}
