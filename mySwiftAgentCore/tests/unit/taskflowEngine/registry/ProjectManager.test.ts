/**
 * TaskFlow ProjectManager Unit Tests
 *
 * Issue #363: Project lifecycle management for TaskFlow
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  TaskFlowProjectManager,
  createTaskFlowProjectManager,
  type TaskFlowProjectInfo,
} from '../../../../src/taskflowEngine/registry/ProjectManager.js';

describe('TaskFlowProjectManager', () => {
  let manager: TaskFlowProjectManager;

  beforeEach(() => {
    manager = new TaskFlowProjectManager();
  });

  describe('createProject', () => {
    it('should create a new project', () => {
      const project = manager.createProject('test_project', 'Test Project', 'A test project');

      expect(project.projectId).toBe('test_project');
      expect(project.name).toBe('Test Project');
      expect(project.description).toBe('A test project');
      expect(project.createdAt).toBeInstanceOf(Date);
      expect(project.updatedAt).toBeInstanceOf(Date);
    });

    it('should throw error if project already exists', () => {
      manager.createProject('test_project', 'Test Project');

      expect(() => {
        manager.createProject('test_project', 'Duplicate Project');
      }).toThrow('Project test_project already exists');
    });

    it('should create project without description', () => {
      const project = manager.createProject('simple_project', 'Simple Project');

      expect(project.projectId).toBe('simple_project');
      expect(project.description).toBeUndefined();
    });
  });

  describe('getProject', () => {
    it('should return project by id', () => {
      manager.createProject('test_project', 'Test Project');

      const project = manager.getProject('test_project');
      expect(project).toBeDefined();
      expect(project?.projectId).toBe('test_project');
    });

    it('should return undefined for non-existent project', () => {
      const project = manager.getProject('non_existent');
      expect(project).toBeUndefined();
    });
  });

  describe('listProjects', () => {
    it('should return all projects', () => {
      manager.createProject('project_1', 'Project 1');
      manager.createProject('project_2', 'Project 2');

      const projects = manager.listProjects();
      expect(projects).toHaveLength(2);
      expect(projects.map(p => p.projectId)).toContain('project_1');
      expect(projects.map(p => p.projectId)).toContain('project_2');
    });

    it('should return empty array when no projects', () => {
      const projects = manager.listProjects();
      expect(projects).toEqual([]);
    });
  });

  describe('updateProject', () => {
    beforeEach(() => {
      manager.createProject('test_project', 'Test Project', 'Original description');
    });

    it('should update project name', () => {
      const updated = manager.updateProject('test_project', { name: 'Updated Name' });

      expect(updated?.name).toBe('Updated Name');
    });

    it('should update project description', () => {
      const updated = manager.updateProject('test_project', { description: 'New description' });

      expect(updated?.description).toBe('New description');
    });

    it('should update multiple fields', () => {
      const updated = manager.updateProject('test_project', {
        name: 'New Name',
        description: 'New description',
      });

      expect(updated?.name).toBe('New Name');
      expect(updated?.description).toBe('New description');
    });

    it('should return undefined for non-existent project', () => {
      const updated = manager.updateProject('non_existent', { name: 'New Name' });
      expect(updated).toBeUndefined();
    });

    it('should update updatedAt timestamp', () => {
      const original = manager.getProject('test_project');
      const originalUpdatedAt = original?.updatedAt;

      // Small delay to ensure timestamp difference
      const updated = manager.updateProject('test_project', { name: 'New Name' });

      expect(updated?.updatedAt.getTime()).toBeGreaterThanOrEqual(
        originalUpdatedAt?.getTime() ?? 0
      );
    });
  });

  describe('deleteProject', () => {
    beforeEach(() => {
      manager.createProject('test_project', 'Test Project');
    });

    it('should delete existing project', () => {
      const result = manager.deleteProject('test_project');

      expect(result).toBe(true);
      expect(manager.getProject('test_project')).toBeUndefined();
    });

    it('should return false for non-existent project', () => {
      const result = manager.deleteProject('non_existent');
      expect(result).toBe(false);
    });
  });

  describe('hasProject', () => {
    it('should return true for existing project', () => {
      manager.createProject('test_project', 'Test Project');

      expect(manager.hasProject('test_project')).toBe(true);
    });

    it('should return false for non-existent project', () => {
      expect(manager.hasProject('non_existent')).toBe(false);
    });
  });

  describe('getStats', () => {
    it('should return project statistics', () => {
      manager.createProject('project_1', 'Project 1');
      manager.createProject('project_2', 'Project 2');

      const stats = manager.getStats();
      expect(stats.totalProjects).toBe(2);
    });

    it('should return zero when no projects', () => {
      const stats = manager.getStats();
      expect(stats.totalProjects).toBe(0);
    });
  });

  describe('clear', () => {
    it('should clear all projects', () => {
      manager.createProject('project_1', 'Project 1');
      manager.createProject('project_2', 'Project 2');

      manager.clear();

      expect(manager.listProjects()).toHaveLength(0);
    });
  });
});

describe('createTaskFlowProjectManager factory', () => {
  it('should create a TaskFlowProjectManager instance', () => {
    const manager = createTaskFlowProjectManager();
    expect(manager).toBeInstanceOf(TaskFlowProjectManager);
  });
});
