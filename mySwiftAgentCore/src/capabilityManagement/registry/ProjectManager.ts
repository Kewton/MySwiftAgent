/**
 * ProjectManager - Project lifecycle management
 *
 * Issue #365: Manages project creation, retrieval, and deletion
 * for organizing capabilities.
 */

/**
 * Project information
 */
export interface ProjectInfo {
  projectId: string;
  name: string;
  description?: string;
  createdAt: Date;
  updatedAt: Date;
}

/**
 * Project update payload
 */
export interface ProjectUpdate {
  name?: string;
  description?: string;
}

/**
 * Project statistics
 */
export interface ProjectStats {
  totalProjects: number;
}

/**
 * ProjectManager - Manages project lifecycle
 *
 * Features:
 * - Create and delete projects
 * - Update project metadata
 * - List and query projects
 */
export class ProjectManager {
  private readonly projects: Map<string, ProjectInfo>;

  constructor() {
    this.projects = new Map();
  }

  /**
   * Create a new project
   *
   * @param projectId - Unique project identifier
   * @param name - Display name for the project
   * @param description - Optional project description
   * @returns The created project info
   * @throws Error if project already exists
   */
  createProject(projectId: string, name: string, description?: string): ProjectInfo {
    if (this.projects.has(projectId)) {
      throw new Error(`Project ${projectId} already exists`);
    }

    const now = new Date();
    const project: ProjectInfo = {
      projectId,
      name,
      description,
      createdAt: now,
      updatedAt: now,
    };

    this.projects.set(projectId, project);
    return project;
  }

  /**
   * Get a project by ID
   *
   * @param projectId - The project identifier
   * @returns The project info if found, undefined otherwise
   */
  getProject(projectId: string): ProjectInfo | undefined {
    return this.projects.get(projectId);
  }

  /**
   * List all projects
   *
   * @returns Array of all project info objects
   */
  listProjects(): ProjectInfo[] {
    return Array.from(this.projects.values());
  }

  /**
   * Delete a project
   *
   * @param projectId - The project identifier
   * @returns true if deleted, false if not found
   */
  deleteProject(projectId: string): boolean {
    return this.projects.delete(projectId);
  }

  /**
   * Update a project
   *
   * @param projectId - The project identifier
   * @param update - The fields to update
   * @returns The updated project info, or undefined if not found
   */
  updateProject(projectId: string, update: ProjectUpdate): ProjectInfo | undefined {
    const project = this.projects.get(projectId);

    if (!project) {
      return undefined;
    }

    if (update.name !== undefined) {
      project.name = update.name;
    }

    if (update.description !== undefined) {
      project.description = update.description;
    }

    project.updatedAt = new Date();
    this.projects.set(projectId, project);

    return project;
  }

  /**
   * Check if a project exists
   *
   * @param projectId - The project identifier
   * @returns true if project exists
   */
  hasProject(projectId: string): boolean {
    return this.projects.has(projectId);
  }

  /**
   * Get project statistics
   *
   * @returns Statistics about managed projects
   */
  getStats(): ProjectStats {
    return {
      totalProjects: this.projects.size,
    };
  }

  /**
   * Clear all projects
   */
  clear(): void {
    this.projects.clear();
  }
}

/**
 * Factory function to create ProjectManager
 */
export function createProjectManager(): ProjectManager {
  return new ProjectManager();
}
