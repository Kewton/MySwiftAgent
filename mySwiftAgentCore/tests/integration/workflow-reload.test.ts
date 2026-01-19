/**
 * Workflow Reload Integration Tests
 *
 * Issue #375: Integration tests for workflow reload functionality
 * Issue #375 (iteration-2): Added API endpoint integration tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Hono } from 'hono';
import { WorkflowReloader } from '../../src/taskflowEngine/loader/WorkflowReloader.js';
import { WorkflowLoader } from '../../src/taskflowEngine/loader/WorkflowLoader.js';
import { WorkflowRegistry } from '../../src/taskflowEngine/registry/WorkflowRegistry.js';
import { FileSystemWatcher } from '../../src/taskflowEngine/watcher/FileSystemWatcher.js';
import { createTaskFlowReloadRoutes, type ReloadHandlerDependencies } from '../../src/api/routes/taskflow-reload.js';
import * as fs from 'fs/promises';
import * as path from 'path';

describe('Workflow Reload Integration', () => {
  let loader: WorkflowLoader;
  let registry: WorkflowRegistry;
  let reloader: WorkflowReloader;
  const testBasePath = '/tmp/test-reload-workflows';

  beforeEach(async () => {
    // Create test directory structure
    await fs.mkdir(path.join(testBasePath, 'project1', 'workflows'), { recursive: true });

    // Create test workflow file
    const testWorkflow = {
      workflow_name: 'test_workflow',
      input_schema: {
        type: 'object',
        properties: {
          input: { type: 'string' },
        },
      },
      output_schema: {
        type: 'object',
        properties: {
          output: { type: 'string' },
        },
      },
      steps: [
        {
          id: 'step1',
          type: 'transform',
          config: {
            mapping: { result: '$.input' },
          },
          params: {},
        },
      ],
      output: {
        output: '$steps.step1.result',
      },
    };

    await fs.writeFile(
      path.join(testBasePath, 'project1', 'workflows', 'test.json'),
      JSON.stringify(testWorkflow, null, 2)
    );

    loader = new WorkflowLoader({ basePath: testBasePath });
    registry = new WorkflowRegistry();
    reloader = new WorkflowReloader(loader, registry);
  });

  afterEach(async () => {
    // Cleanup test directory
    try {
      await fs.rm(testBasePath, { recursive: true, force: true });
    } catch {
      // Ignore cleanup errors
    }
  });

  describe('full reload cycle', () => {
    it('should load workflows from filesystem and register them', async () => {
      const result = await reloader.reloadProject('project1');

      expect(result.success).toBe(true);
      expect(result.reloadedCount).toBe(1);
      expect(result.workflowNames).toContain('test_workflow');

      // Verify workflow is in registry
      const workflows = registry.getByProject('project1');
      expect(workflows).toHaveLength(1);
      expect(workflows[0].name).toBe('test_workflow');
    });

    it('should update registry when workflow file changes', async () => {
      // Initial load
      await reloader.reloadProject('project1');

      // Update workflow file
      const updatedWorkflow = {
        workflow_name: 'test_workflow_updated',
        input_schema: { type: 'object', properties: {} },
        output_schema: { type: 'object', properties: {} },
        steps: [
          {
            id: 'step1',
            type: 'transform',
            config: { mapping: { result: '$.input' } },
            params: {},
          },
        ],
        output: {},
      };

      await fs.writeFile(
        path.join(testBasePath, 'project1', 'workflows', 'test.json'),
        JSON.stringify(updatedWorkflow, null, 2)
      );

      // Reload
      const result = await reloader.reloadProject('project1');

      expect(result.success).toBe(true);

      // Verify updated workflow is in registry
      const workflows = registry.getByProject('project1');
      expect(workflows.some((w) => w.name === 'test_workflow_updated')).toBe(true);
    });

    it('should handle multiple projects', async () => {
      // Create second project
      await fs.mkdir(path.join(testBasePath, 'project2', 'workflows'), { recursive: true });
      await fs.writeFile(
        path.join(testBasePath, 'project2', 'workflows', 'workflow2.json'),
        JSON.stringify({
          workflow_name: 'workflow2',
          input_schema: { type: 'object', properties: {} },
          output_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'step1',
              type: 'transform',
              config: { mapping: { result: '$.input' } },
              params: {},
            },
          ],
          output: {},
        })
      );

      // Reload all projects
      const result = await reloader.reloadAll();

      expect(result.success).toBe(true);
      expect(result.projectResults).toHaveLength(2);

      // Verify both projects have workflows
      expect(registry.getByProject('project1')).toHaveLength(1);
      expect(registry.getByProject('project2')).toHaveLength(1);
    });
  });

  describe('error handling', () => {
    it('should handle invalid JSON gracefully', async () => {
      // Write invalid JSON
      await fs.writeFile(
        path.join(testBasePath, 'project1', 'workflows', 'invalid.json'),
        '{ invalid json }'
      );

      const result = await reloader.reloadProject('project1');

      // Should still succeed for valid workflows
      expect(result.reloadedCount).toBeGreaterThanOrEqual(0);
    });

    it('should handle missing project directory', async () => {
      const result = await reloader.reloadProject('nonexistent_project');

      expect(result.success).toBe(true);
      expect(result.reloadedCount).toBe(0);
    });
  });

  describe('FileSystemWatcher integration', () => {
    it('should create watcher instance', () => {
      const watcher = new FileSystemWatcher();
      expect(watcher).toBeInstanceOf(FileSystemWatcher);
    });

    it('should trigger reload on file change', async () => {
      const watcher = new FileSystemWatcher();
      const reloadCallback = vi.fn();

      // Set up watcher with callback that reloads
      await watcher.watch(testBasePath, async (event) => {
        if (event.path.endsWith('.json')) {
          reloadCallback(event);
        }
      });

      // Simulate file change
      watcher.simulateFileChange('change', path.join(testBasePath, 'project1', 'workflows', 'test.json'));

      // Wait for debounce
      await new Promise((resolve) => setTimeout(resolve, 350));

      expect(reloadCallback).toHaveBeenCalled();

      await watcher.stop();
    });
  });

  /**
   * Issue #375 (iteration-2): API Endpoint Integration Tests
   * Tests that verify the reload API is accessible and functional
   */
  describe('Reload API endpoint integration', () => {
    let app: Hono;
    let reloadDeps: ReloadHandlerDependencies;

    beforeEach(() => {
      // Create app with reload routes mounted
      app = new Hono();
      reloadDeps = { reloader };
      const reloadRoutes = createTaskFlowReloadRoutes(reloadDeps);
      app.route('/api/v1/taskflow', reloadRoutes);
    });

    it('should have POST /api/v1/taskflow/reload endpoint accessible', async () => {
      // Make request to reload endpoint
      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: 'project1' }),
      });

      const res = await app.fetch(req);

      // Verify endpoint is accessible (not 404)
      expect(res.status).not.toBe(404);
      // Should be 200 (success) or 400/500 (handled error)
      expect([200, 400, 500]).toContain(res.status);
    });

    it('should reload single project via API', async () => {
      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: 'project1' }),
      });

      const res = await app.fetch(req);
      const body = await res.json() as { success: boolean; reloadedCount?: number; workflowNames?: string[] };

      expect(res.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.reloadedCount).toBe(1);
      expect(body.workflowNames).toContain('test_workflow');
    });

    it('should reload single workflow file via API', async () => {
      const filePath = path.join(testBasePath, 'project1', 'workflows', 'test.json');
      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: 'project1',
          file_path: filePath,
        }),
      });

      const res = await app.fetch(req);
      const body = await res.json() as { success: boolean; workflowName?: string };

      expect(res.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.workflowName).toBe('test_workflow');
    });

    it('should reload all projects via API when no project specified', async () => {
      // Create second project for full reload test
      await fs.mkdir(path.join(testBasePath, 'project2', 'workflows'), { recursive: true });
      await fs.writeFile(
        path.join(testBasePath, 'project2', 'workflows', 'workflow2.json'),
        JSON.stringify({
          workflow_name: 'workflow2',
          input_schema: { type: 'object', properties: {} },
          output_schema: { type: 'object', properties: {} },
          steps: [
            {
              id: 'step1',
              type: 'transform',
              config: { mapping: { result: '$.input' } },
              params: {},
            },
          ],
          output: {},
        })
      );

      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      const res = await app.fetch(req);
      const body = await res.json() as {
        success: boolean;
        totalReloaded?: number;
        projectResults?: Array<{ reloadedCount: number }>;
      };

      expect(res.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.totalReloaded).toBeGreaterThanOrEqual(2);
      expect(body.projectResults).toBeDefined();
      expect(body.projectResults!.length).toBeGreaterThanOrEqual(2);
    });

    it('should handle invalid project gracefully via API', async () => {
      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project: 'nonexistent_project' }),
      });

      const res = await app.fetch(req);
      const body = await res.json() as { success: boolean; reloadedCount: number };

      // Should succeed with 0 reloads for nonexistent project
      expect(res.status).toBe(200);
      expect(body.success).toBe(true);
      expect(body.reloadedCount).toBe(0);
    });

    it('should return error for invalid file path via API', async () => {
      const req = new Request('http://localhost/api/v1/taskflow/reload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project: 'project1',
          file_path: '/nonexistent/path/workflow.json',
        }),
      });

      const res = await app.fetch(req);
      const body = await res.json() as { success: boolean; error?: string };

      expect(res.status).toBe(400);
      expect(body.success).toBe(false);
      expect(body.error).toBeDefined();
    });
  });
});
