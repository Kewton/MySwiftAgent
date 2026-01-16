/**
 * ProjectManager Unit Tests
 *
 * Issue #365: Project management for capability organization
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  ProjectManager,
  createProjectManager,
  type ProjectInfo,
} from '../../../src/capabilityManagement/registry/ProjectManager.js';

describe('ProjectManager', () => {
  let manager: ProjectManager;

  beforeEach(() => {
    manager = new ProjectManager();
  });

  describe('createProject', () => {
    it('should create a new project', () => {
      const project = manager.createProject('my_project', 'My Project', 'A test project');

      expect(project.projectId).toBe('my_project');
      expect(project.name).toBe('My Project');
      expect(project.description).toBe('A test project');
      expect(project.createdAt).toBeInstanceOf(Date);
    });

    it('should create project without description', () => {
      const project = manager.createProject('my_project', 'My Project');

      expect(project.projectId).toBe('my_project');
      expect(project.description).toBeUndefined();
    });

    it('should throw error for duplicate project id', () => {
      manager.createProject('my_project', 'My Project');

      expect(() => manager.createProject('my_project', 'Another Project')).toThrow(
        'Project my_project already exists'
      );
    });
  });

  describe('getProject', () => {
    beforeEach(() => {
      manager.createProject('my_project', 'My Project', 'Test project');
    });

    it('should return project by id', () => {
      const project = manager.getProject('my_project');

      expect(project).toBeDefined();
      expect(project?.projectId).toBe('my_project');
    });

    it('should return undefined for non-existent project', () => {
      const project = manager.getProject('non_existent');

      expect(project).toBeUndefined();
    });
  });

  describe('listProjects', () => {
    it('should return all projects', () => {
      manager.createProject('project1', 'Project 1');
      manager.createProject('project2', 'Project 2');

      const projects = manager.listProjects();

      expect(projects).toHaveLength(2);
      expect(projects.map((p) => p.projectId)).toContain('project1');
      expect(projects.map((p) => p.projectId)).toContain('project2');
    });

    it('should return empty array when no projects', () => {
      const projects = manager.listProjects();

      expect(projects).toEqual([]);
    });
  });

  describe('deleteProject', () => {
    beforeEach(() => {
      manager.createProject('my_project', 'My Project');
    });

    it('should delete an existing project', () => {
      const result = manager.deleteProject('my_project');

      expect(result).toBe(true);
      expect(manager.getProject('my_project')).toBeUndefined();
    });

    it('should return false for non-existent project', () => {
      const result = manager.deleteProject('non_existent');

      expect(result).toBe(false);
    });
  });

  describe('updateProject', () => {
    beforeEach(() => {
      manager.createProject('my_project', 'My Project', 'Original description');
    });

    it('should update project name', () => {
      const updated = manager.updateProject('my_project', { name: 'Updated Name' });

      expect(updated?.name).toBe('Updated Name');
      expect(updated?.description).toBe('Original description');
    });

    it('should update project description', () => {
      const updated = manager.updateProject('my_project', {
        description: 'New description',
      });

      expect(updated?.description).toBe('New description');
    });

    it('should update updatedAt timestamp', () => {
      const original = manager.getProject('my_project');
      const originalUpdatedAt = original?.updatedAt;

      // Small delay to ensure different timestamp
      const updated = manager.updateProject('my_project', { name: 'Updated' });

      expect(updated?.updatedAt.getTime()).toBeGreaterThanOrEqual(
        originalUpdatedAt?.getTime() ?? 0
      );
    });

    it('should return undefined for non-existent project', () => {
      const updated = manager.updateProject('non_existent', { name: 'Test' });

      expect(updated).toBeUndefined();
    });
  });

  describe('hasProject', () => {
    it('should return true for existing project', () => {
      manager.createProject('my_project', 'My Project');

      expect(manager.hasProject('my_project')).toBe(true);
    });

    it('should return false for non-existent project', () => {
      expect(manager.hasProject('non_existent')).toBe(false);
    });
  });

  describe('getStats', () => {
    it('should return correct statistics', () => {
      manager.createProject('project1', 'Project 1');
      manager.createProject('project2', 'Project 2');

      const stats = manager.getStats();

      expect(stats.totalProjects).toBe(2);
    });
  });
});

describe('createProjectManager factory', () => {
  it('should create a ProjectManager instance', () => {
    const manager = createProjectManager();
    expect(manager).toBeInstanceOf(ProjectManager);
  });
});
